from typing import List, Literal, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from backend.app.config import get_settings
from backend.app.genai_client import GeminiClient, GeminiPingResult


router = APIRouter()


class HealthCheck(BaseModel):
    name: str
    status: Literal["ok", "error"]
    details: Optional[str] = None


class HealthResponse(BaseModel):
    status: Literal["ok", "error"]
    checks: List[HealthCheck]


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """
    Basic health check endpoint.

    Verifies configuration is loaded and, when possible, that the
    GenAI client can be instantiated and a lightweight ping can be
    executed without raising unexpected exceptions.
    """
    checks: list[HealthCheck] = []

    settings = get_settings()

    if settings.gemini_api_key:
        config_status: Literal["ok", "error"] = "ok"
        config_details = "GEMINI_API_KEY configured"
    else:
        config_status = "error"
        config_details = "GEMINI_API_KEY not configured"

    checks.append(
        HealthCheck(
            name="config",
            status=config_status,
            details=config_details,
        )
    )

    if config_status == "ok":
        try:
            client = GeminiClient()
            ping: GeminiPingResult = client.ping_model()
            if ping.ok:
                checks.append(
                    HealthCheck(
                        name="genai_client",
                        status="ok",
                        details=f"model={ping.model_id}",
                    )
                )
            else:
                # Avoid leaking sensitive details, but surface a concise reason.
                truncated_error = (
                    ping.error[:200] if ping.error is not None else "ping_model failed"
                )
                checks.append(
                    HealthCheck(
                        name="genai_client",
                        status="error",
                        details=truncated_error,
                    )
                )
        except Exception:
            checks.append(
                HealthCheck(
                    name="genai_client",
                    status="error",
                    details="exception while initializing or pinging GenAI client",
                )
            )
    else:
        checks.append(
            HealthCheck(
                name="genai_client",
                status="error",
                details="skipped GenAI ping because GEMINI_API_KEY is not configured",
            )
        )

    overall_status: Literal["ok", "error"] = (
        "ok" if all(check.status == "ok" for check in checks) else "error"
    )

    return HealthResponse(status=overall_status, checks=checks)

