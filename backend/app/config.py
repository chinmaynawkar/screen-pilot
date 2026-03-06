from functools import lru_cache
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel

# Load .env from backend/ (parent of app/) or project root so GEMINI_API_KEY is set
_backend_dir = Path(__file__).resolve().parent.parent
for env_path in (_backend_dir / ".env", _backend_dir.parent / ".env"):
    if env_path.exists():
        load_dotenv(env_path)
        break


class Settings(BaseModel):
    """
    Central application configuration.

    Values are loaded from environment variables. This keeps all config
    access in one place and avoids scattering os.getenv calls across
    the codebase.
    """

    gemini_api_key: str
    gcp_project_id: Optional[str] = None
    gcp_region: Optional[str] = None
    timesheet_url: str
    gemini_action_model_id: str
    gemini_action_fallback_model_id: Optional[str] = None

    @classmethod
    def from_env(cls) -> "Settings":
        port = os.environ.get("PORT", "8000")
        default_timesheet_url = f"http://127.0.0.1:{port}/api/timesheet-demo"
        # Prefer a stable, low-cost multimodal model for free-tier usage.
        # The computer-use preview models often have free-tier quota set to 0.
        default_action_model_id = "gemini-2.5-flash-lite"
        return cls(
            gemini_api_key=os.environ.get("GEMINI_API_KEY", ""),
            gcp_project_id=os.environ.get("GCP_PROJECT_ID"),
            gcp_region=os.environ.get("GCP_REGION"),
            timesheet_url=os.environ.get("TIMESHEET_URL", default_timesheet_url),
            gemini_action_model_id=os.environ.get(
                "GEMINI_ACTION_MODEL_ID", default_action_model_id
            ),
            gemini_action_fallback_model_id=os.environ.get(
                "GEMINI_ACTION_FALLBACK_MODEL_ID", "gemini-3-flash-preview"
            ),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached Settings instance.

    The first call reads from the environment; subsequent calls reuse
    the same object for the lifetime of the process.
    """

    return Settings.from_env()

