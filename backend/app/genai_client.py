from dataclasses import dataclass
from typing import Optional

from google import genai

from backend.app.config import get_settings


DEFAULT_HEALTH_MODEL_ID = "gemini-3-flash-preview"


@dataclass
class GeminiPingResult:
    ok: bool
    model_id: Optional[str] = None
    error: Optional[str] = None


class GeminiClient:
    """
    Thin wrapper around the official Google GenAI Python SDK client.

    This adapter centralizes client configuration and exposes a very
    small surface area that the rest of the application can depend on.
    """

    def __init__(self) -> None:
        settings = get_settings()
        # The GenAI client will also read GEMINI_API_KEY from the
        # environment if not provided explicitly, but we wire it here
        # to keep configuration explicit.
        self._client = genai.Client(api_key=settings.gemini_api_key or None)

    def ping_model(self, model: str = DEFAULT_HEALTH_MODEL_ID) -> GeminiPingResult:
        """
        Perform a minimal call to a text-capable Gemini model to verify
        that the client and credentials are working.
        """
        try:
            self._client.models.generate_content(
                model=model,
                contents="health check",
            )
            return GeminiPingResult(ok=True, model_id=model)
        except Exception as exc:
            # The error message should not contain secrets, but we still
            # treat it as an opaque string and let callers decide how
            # much detail to surface.
            return GeminiPingResult(ok=False, model_id=model, error=str(exc))

