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

# When using GCP persistence, ensure ADC uses a service account key so V4 signed URLs work.
# See: https://cloud.google.com/docs/authentication/application-default-credentials
_DEFAULT_GCP_KEY = "gen-lang-client-0188455373-70b848cfc13c.json"
_creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
_resolved = None
if _creds_path:
    p = Path(_creds_path)
    if not p.is_absolute():
        p = (_backend_dir / p).resolve()
    if p.exists():
        _resolved = p
if _resolved is None and os.environ.get("PERSISTENCE_BACKEND", "").strip().lower() == "gcp":
    _default_key = _backend_dir / _DEFAULT_GCP_KEY
    if _default_key.exists():
        _resolved = _default_key.resolve()
if _resolved is not None:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(_resolved)


class Settings(BaseModel):
    """
    Central application configuration.

    Values are loaded from environment variables. This keeps all config
    access in one place and avoids scattering os.getenv calls across
    the codebase.
    """

    gemini_api_key: str
    # Persistence backend selection: "in_memory" (default) or "gcp".
    persistence_backend: str = "in_memory"
    gcp_project_id: Optional[str] = None
    gcp_region: Optional[str] = None
    gcs_bucket_name: Optional[str] = None
    gcs_signed_url_ttl_seconds: int = 900
    timesheet_url: str
    gemini_action_model_id: str
    gemini_action_fallback_model_id: Optional[str] = None
    runs_collection: str = "runs"
    run_steps_subcollection: str = "runSteps"
    firestore_database_id: Optional[str] = None  # None = use "(default)" database

    @classmethod
    def from_env(cls) -> "Settings":
        port = os.environ.get("PORT", "8000")
        default_timesheet_url = f"http://127.0.0.1:{port}/api/timesheet-demo"
        # Prefer a stable, low-cost multimodal model for free-tier usage.
        # The computer-use preview models often have free-tier quota set to 0.
        default_action_model_id = "gemini-2.5-flash-lite"
        return cls(
            gemini_api_key=os.environ.get("GEMINI_API_KEY", ""),
            persistence_backend=os.environ.get("PERSISTENCE_BACKEND", "in_memory"),
            gcp_project_id=os.environ.get("GCP_PROJECT_ID"),
            gcp_region=os.environ.get("GCP_REGION"),
            gcs_bucket_name=os.environ.get("GCS_BUCKET_NAME"),
            gcs_signed_url_ttl_seconds=int(
                os.environ.get("GCS_SIGNED_URL_TTL_SECONDS", "900")
            ),
            timesheet_url=os.environ.get("TIMESHEET_URL", default_timesheet_url),
            gemini_action_model_id=os.environ.get(
                "GEMINI_ACTION_MODEL_ID", default_action_model_id
            ),
            gemini_action_fallback_model_id=os.environ.get(
                "GEMINI_ACTION_FALLBACK_MODEL_ID", "gemini-3-flash-preview"
            ),
            runs_collection=os.environ.get("RUNS_COLLECTION", "runs"),
            run_steps_subcollection=os.environ.get("RUN_STEPS_SUBCOLLECTION", "runSteps"),
            firestore_database_id=os.environ.get("FIRESTORE_DATABASE_ID") or None,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached Settings instance.

    The first call reads from the environment; subsequent calls reuse
    the same object for the lifetime of the process.
    """

    return Settings.from_env()

