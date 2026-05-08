# Security Model

1. **API Keys**: Google Maps API keys are restricted by HTTP referrer to only allow the Firebase Hosting domain. Backend Google APIs use a Service Account with least-privilege IAM roles, eliminating the need for API keys in the backend.
2. **Secrets Management**: Database passwords, external API keys, and configuration secrets are stored in GCP Secret Manager and injected into Cloud Run as environment variables.
3. **Authentication**: Firebase Authentication handles user identity. The frontend passes a JWT token in the `Authorization` header, which the backend validates using the Firebase Admin SDK.
4. **Data Validation**: FastAPI and Pydantic enforce strict schema validation for all inputs and outputs.
5. **AI Safety**: Prompts sent to Gemini are sanitized. Responses from Gemini are strictly parsed into Pydantic models; raw AI output is never trusted blindly.
6. **Rate Limiting**: Implementation of rate limiting on the backend API prevents abuse.
7. **CORS**: Configurable via the `CORS_ORIGINS` environment variable.
