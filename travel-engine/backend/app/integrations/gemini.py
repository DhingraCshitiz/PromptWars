from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

last_gemini_error: str | None = None

try:
    import google.generativeai as genai
    from google.generativeai.types import GenerationConfig

    GENAI_PKG = True
except ImportError:
    GENAI_PKG = False
    GenerationConfig = None  # type: ignore[misc, assignment]

try:
    import vertexai
    from vertexai.generative_models import (
        GenerativeModel as VertexGenerativeModel,
        GenerationConfig as VertexGenerationConfig,
    )

    VERTEX_PKG = True
except ImportError:
    VERTEX_PKG = False
    VertexGenerationConfig = None  # type: ignore[misc, assignment]
    VertexGenerativeModel = None  # type: ignore[misc, assignment]
def _genai_safety_settings() -> Any:
    """Reduce false blocks on innocuous travel planning prompts."""
    if not GENAI_PKG:
        return None
    try:
        from google.generativeai.types import HarmBlockThreshold, HarmCategory

        return {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        }
    except Exception:
        return None


def planner_diagnostics() -> Dict[str, Any]:
    """Read-only hints for debugging why AI vs heuristic runs."""
    raw_key = settings.GEMINI_API_KEY or ""
    return {
        "google_generativeai_installed": GENAI_PKG,
        "gemini_api_key_configured": bool(raw_key.strip()),
        "gemini_model": settings.GEMINI_MODEL,
        "use_mock_google_env": settings.USE_MOCK_GOOGLE,
        "vertex_sdk_installed": VERTEX_PKG,
        "last_gemini_error": last_gemini_error,
        "hints": (
            "If gemini_api_key_configured is false: add GEMINI_API_KEY to backend/.env (no quotes), "
            "then restart uvicorn.\n"
            "If last_gemini_error is set after creating a trip: the SDK call threw (often blocked/"
            'empty response, invalid model id, quota). Try GEMINI_MODEL=gemini-2.5-flash or '
            "gemini-2.5-flash-lite.\n"
            'Access response.text raises when candidates are blocked — check finish_reason.'
        ),
    }


def _prompt_for_model(constraints: Dict[str, Any]) -> str:
    prefs = constraints["preferences"]
    interests = ", ".join(prefs.get("interests") or ["general exploration"])
    dietary = ", ".join(prefs.get("dietary_restrictions") or []) or "none specified"
    accessibility = ", ".join(prefs.get("accessibility_needs") or []) or "none specified"

    return f"""
You are an expert travel planner. Create a tailored, realistic itinerary grounded in the traveler profile.

Destination: {constraints["destination"]}
Trip window: {constraints.get("start_date")} → {constraints.get("end_date")}
Days to cover: {constraints["days"]} (produce exactly this many `days` entries)

Traveler profile:
- Budget: {prefs["budget"]}
- Pace: {prefs["pace"]}
- Interests: {interests}
- Dietary: {dietary}
- Accessibility: {accessibility}

Rules:
1) `day_index` must run 1…{constraints["days"]} in order.
2) Stop counts by pace: relaxed 2–3, moderate 3–4, fast 4–6 stops per day (pick coherently).
3) Names must feel specific to the destination and interests (avoid generic “Top sight” placeholders).
4) Descriptions: 2–3 helpful sentences (timing, why it fits, practical tip). Mention dietary/accessibility constraints when relevant.
5) Return ONLY valid JSON (no markdown fences, no commentary) with this shape:
{{
  "days": [
    {{
      "day_index": 1,
      "stops": [
        {{
          "name": "...",
          "description": "...",
          "place_id": "unknown_or_estimated"
        }}
      ]
    }}
  ]
}}
"""


def _unwrap_json_markdown(blob: str) -> str:
    text = blob.strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _explain_empty_response(gen_response: Any) -> str:
    cand = getattr(gen_response, "candidates", None) or []
    if not cand:
        pf = getattr(gen_response, "prompt_feedback", None)
        pb = getattr(pf, "block_reason", None) if pf is not None else None
        return f"No candidates returned (prompt_feedback.block_reason={pb!r})."
    first = cand[0]
    fr_name = getattr(getattr(first, "finish_reason", None), "name", None) or getattr(
        first,
        "finish_reason",
        None,
    )
    safety = getattr(first, "safety_ratings", None)
    return f"finish_reason={fr_name!r} safety_ratings={safety!r}"


def _extract_response_text(gen_response: Any) -> str:
    """Never use getattr(..., 'text') — `.text` is a raising property when output is blocked."""
    try:
        text = gen_response.text
        if text:
            return text
    except Exception as exc:
        logger.warning("Gemini response.text unreadable (%s): %s", _explain_empty_response(gen_response), exc)

    candidates = getattr(gen_response, "candidates", None) or []
    if not candidates:
        return ""

    first = candidates[0]
    content = getattr(first, "content", None)
    if not content:
        return ""

    parts = getattr(content, "parts", None) or []
    chunks = []
    for part in parts:
        t = getattr(part, "text", None)
        if t:
            chunks.append(t)
    return "".join(chunks)


def _safely_raise_if_blocked(gen_response: Any) -> None:
    feedback = getattr(gen_response, "prompt_feedback", None)
    if feedback is None:
        return
    block = getattr(feedback, "block_reason", None)
    if block:
        raise RuntimeError(f"Gemini blocked the prompt ({block}).")


def _parse_json_blob(blob: str) -> Dict[str, Any]:
    blob = blob.strip()
    if not blob:
        raise ValueError("empty json blob")
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        return json.loads(_unwrap_json_markdown(blob))


def _invoke_genai(
    model: Any,
    prompt: str,
    *,
    json_mode: bool,
    safety_settings: Optional[Any],
) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {}
    if safety_settings:
        kwargs["safety_settings"] = safety_settings

    if json_mode and GenerationConfig is not None:
        kwargs["generation_config"] = GenerationConfig(response_mime_type="application/json")
    elif json_mode:
        kwargs["generation_config"] = {"response_mime_type": "application/json"}

    gen_response = model.generate_content(prompt, **kwargs)

    _safely_raise_if_blocked(gen_response)

    blob = _extract_response_text(gen_response).strip()
    if not blob:
        raise RuntimeError(_explain_empty_response(gen_response))

    return _parse_json_blob(blob)


def _call_genai_sync(model: Any, prompt: str) -> Dict[str, Any]:
    """
    Gemini Dev API — try JSON MIME first; many models/accounts mishandle MIME or block `.text`; fall back.
    """
    global last_gemini_error
    safety_settings = _genai_safety_settings()
    errs: List[str] = []

    try:
        data = _invoke_genai(model, prompt, json_mode=True, safety_settings=safety_settings)
        last_gemini_error = None
        return data
    except Exception as exc:
        errs.append(f"json_mime:{exc}")

    try:
        extra = '\nRespond with ONE raw JSON object only. Do not wrap in markdown. Start with `{` end with `}`.'
        data = _invoke_genai(model, prompt + extra, json_mode=False, safety_settings=safety_settings)
        last_gemini_error = None
        return data
    except Exception as exc:
        errs.append(f"plain_text:{exc}")

    last_gemini_error = "; ".join(errs)
    raise RuntimeError(last_gemini_error)


def _call_vertex_sync(model: Any, prompt: str) -> Dict[str, Any]:
    response = model.generate_content(
        prompt,
        generation_config=VertexGenerationConfig(response_mime_type="application/json"),
    )
    try:
        blob = (response.text or "").strip()
    except Exception:
        blob = _extract_response_text(response).strip()
    return _parse_json_blob(blob or "{}")


class GeminiPlannerClient:
    """Prefer Gemini Developer API (`GEMINI_API_KEY`), then Vertex when enabled, then heuristic."""

    def __init__(self) -> None:
        global last_gemini_error

        self._mode = "fallback"
        self._genai_model = None
        self._vertex_model = None

        if settings.GEMINI_API_KEY and GENAI_PKG:
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self._genai_model = genai.GenerativeModel(settings.GEMINI_MODEL)
                self._mode = "genai"
                logger.info(
                    "Planner using Gemini Developer API model=%s (API key configured).",
                    settings.GEMINI_MODEL,
                )
                return
            except Exception as exc:
                last_gemini_error = repr(exc)
                logger.warning("GEMINI_API_KEY set but google-generativeai init failed: %s", exc)

        if not settings.USE_MOCK_GOOGLE and VERTEX_PKG:
            try:
                vertexai.init(project=settings.GOOGLE_CLOUD_PROJECT, location="us-central1")
                self._vertex_model = VertexGenerativeModel(settings.GEMINI_MODEL)
                self._mode = "vertex"
                logger.info(
                    "Planner using Vertex AI model=%s project=%s",
                    settings.GEMINI_MODEL,
                    settings.GOOGLE_CLOUD_PROJECT,
                )
                return
            except Exception as exc:
                last_gemini_error = repr(exc)
                logger.warning("Vertex init failed; using heuristic itinerary (%s)", exc)

        logger.info(
            "Planner using curated heuristic (%s=no API key sdk=%s, USE_MOCK_GOOGLE=%s).",
            "GEMINI_API_KEY unset" if not settings.GEMINI_API_KEY else "init failed",
            GENAI_PKG,
            settings.USE_MOCK_GOOGLE,
        )

    async def generate_itinerary(self, constraints: Dict[str, Any]) -> Dict[str, Any]:
        global last_gemini_error
        prompt = _prompt_for_model(constraints)

        if self._mode == "genai" and self._genai_model:
            try:
                data = await asyncio.to_thread(_call_genai_sync, self._genai_model, prompt)
                if not isinstance(data, dict):
                    raise TypeError(f"Gemini payload must be an object, got {type(data)}")
                days = data.get("days") or []
                if not isinstance(days, list):
                    raise TypeError("`days` must be a JSON array.")
                last_gemini_error = None
                logger.info("Gemini itinerary success: mode=genai day_count=%s", len(days))
                return data
            except Exception as exc:
                last_gemini_error = repr(exc)
                logger.exception("Gemini API error; falling back to heuristic.")
                return self._curated_local_itinerary(constraints)

        if self._mode == "vertex" and self._vertex_model:
            try:
                data = await asyncio.to_thread(_call_vertex_sync, self._vertex_model, prompt)
                if not isinstance(data, dict):
                    raise TypeError("Vertex Gemini payload malformed.")
                last_gemini_error = None
                return data
            except Exception as exc:
                last_gemini_error = repr(exc)
                logger.exception("Vertex Gemini error; falling back to heuristic.")
                return self._curated_local_itinerary(constraints)

        return self._curated_local_itinerary(constraints)

    def _curated_local_itinerary(self, constraints: Dict[str, Any]) -> Dict[str, Any]:
        dest = constraints["destination"].strip()
        dest_short = dest.split(",")[0].strip() or dest
        days_needed = max(1, int(constraints.get("days", 1)))
        prefs = constraints["preferences"]
        interests: List[str] = prefs.get("interests") or ["local culture & sights"]
        budget = prefs.get("budget", "medium")
        pace = prefs.get("pace", "moderate")
        dietary = prefs.get("dietary_restrictions") or []
        accessibility = prefs.get("accessibility_needs") or []

        pace_stops = {"relaxed": 3, "moderate": 4, "fast": 5}
        stops_per_day = pace_stops.get(pace, 4)
        if budget == "low":
            stops_per_day = max(2, stops_per_day - 1)

        anchors = ["Morning", "Midday", "Afternoon", "Evening", "Night"]
        days_out: List[Dict[str, Any]] = []

        for d in range(days_needed):
            stops: List[Dict[str, Any]] = []
            for s in range(stops_per_day):
                topic = interests[(d + s) % len(interests)]
                slot = anchors[s % len(anchors)]

                dietary_note = ""
                if dietary:
                    dietary_note = f" Food angle: accommodate {', '.join(dietary)}."

                access_note = ""
                if accessibility:
                    access_note = f" Prefer step-free / low-fatigue pacing for: {', '.join(accessibility)}."

                stops.append(
                    {
                        "name": f"{slot} · {topic.title()} immersion in {dest_short}",
                        "description": (
                            f"A curated {pace} paced stop focusing on '{topic}' with a {budget} budget mindset. "
                            f"Spend time exploring facets of {dest_short}, fitting your interests.{dietary_note}"
                            f"{access_note}"
                        ),
                        "place_id": f"local heuristic {d}-{s}",
                    }
                )
            days_out.append({"day_index": d + 1, "stops": stops})

        return {"days": days_out}


_planner_singleton: GeminiPlannerClient | None = None


def get_planner_client() -> GeminiPlannerClient:
    global _planner_singleton
    if _planner_singleton is None:
        _planner_singleton = GeminiPlannerClient()
    return _planner_singleton


def reset_planner_client() -> None:
    """Use after changing GEMINI_* env at runtime (tests / rare hot reload)."""
    global _planner_singleton
    _planner_singleton = None
