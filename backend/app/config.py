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

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            gemini_api_key=os.environ.get("GEMINI_API_KEY", ""),
            gcp_project_id=os.environ.get("GCP_PROJECT_ID"),
            gcp_region=os.environ.get("GCP_REGION"),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached Settings instance.

    The first call reads from the environment; subsequent calls reuse
    the same object for the lifetime of the process.
    """

    return Settings.from_env()

