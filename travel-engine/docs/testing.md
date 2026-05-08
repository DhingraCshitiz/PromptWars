# Testing Strategy

## Backend Testing
- **Framework**: `pytest`
- **Unit Tests**: Test preference scoring, Gemini response parsing (schema validation), prompt injection guards.
- **Integration Tests**: FastAPI `TestClient` is used to test API routes with mocked Google services and database layers.
- **Coverage**: `pytest-cov` generates coverage reports to ensure >80% coverage.
- **Typing**: `mypy` is used for strict static type checking.
- **Linting**: `ruff` is used for fast code linting and formatting.

## Frontend Testing
- **Framework**: Jasmine/Karma for unit tests, Playwright for E2E.
- **Unit Tests**: Test Angular components, RxJS services, and reactive forms.
- **E2E Tests**: Playwright scripts simulate trip creation and itinerary viewing.
- **Accessibility**: `axe-core` tests are run during E2E to ensure WCAG compliance (e.g., proper contrast, keyboard navigation, aria-labels).
