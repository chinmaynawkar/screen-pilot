"""
GCS-backed screenshot store.

Implements IScreenshotStore by uploading PNG bytes to Cloud Storage and
returning a signed URL for temporary access.
"""

from __future__ import annotations

import datetime
from typing import Optional

from google.api_core.exceptions import Forbidden, NotFound, GoogleAPIError
from google.cloud import storage

from backend.app.config import get_settings
from backend.app.domain.ports import IScreenshotStore


def _object_key(run_id: str, step_index: int) -> str:
    """Return a stable object key for a screenshot."""
    return f"runs/{run_id}/steps/{step_index}.png"


class GcsScreenshotStore(IScreenshotStore):
    def __init__(
        self,
        bucket_name: Optional[str] = None,
        *,
        project_id: Optional[str] = None,
        signed_url_ttl_seconds: Optional[int] = None,
    ) -> None:
        settings = get_settings()
        self._bucket_name = bucket_name or settings.gcs_bucket_name
        self._project_id = project_id or settings.gcp_project_id
        self._signed_url_ttl_seconds = (
            signed_url_ttl_seconds or settings.gcs_signed_url_ttl_seconds
        )

        if not self._bucket_name:
            raise ValueError("GCS bucket name is not configured (GCS_BUCKET_NAME).")

        self._client = storage.Client(project=self._project_id)

    def save_screenshot(self, run_id: str, step_index: int, data: bytes) -> str:
        if not data:
            raise ValueError("Screenshot data is empty.")

        object_name = _object_key(run_id, step_index)
        try:
            bucket = self._client.bucket(self._bucket_name)
            blob = bucket.blob(object_name)
            blob.upload_from_string(data, content_type="image/png")

            url = blob.generate_signed_url(
                version="v4",
                expiration=datetime.timedelta(seconds=self._signed_url_ttl_seconds),
                method="GET",
            )
            return url
        except NotFound as exc:
            raise RuntimeError(
                f"GCS bucket or object not found (bucket={self._bucket_name}, "
                f"object={object_name}): {exc}"
            ) from exc
        except Forbidden as exc:
            raise RuntimeError(
                "GCS permission denied when uploading or signing screenshot. "
                "Check that the active credentials have roles/storage.objectUser "
                f"on bucket {self._bucket_name}."
            ) from exc
        except GoogleAPIError as exc:
            raise RuntimeError(f"GCS screenshot upload/signing failed: {exc}") from exc

    def get_screenshot(self, run_id: str, step_index: int) -> Optional[bytes]:
        object_name = _object_key(run_id, step_index)
        try:
            bucket = self._client.bucket(self._bucket_name)
            blob = bucket.blob(object_name)
            if not blob.exists():
                return None
            return blob.download_as_bytes()
        except NotFound:
            return None
        except Forbidden as exc:
            raise RuntimeError(
                "GCS permission denied when reading screenshot. "
                "Check that the active credentials have roles/storage.objectUser "
                f"on bucket {self._bucket_name}."
            ) from exc
        except GoogleAPIError as exc:
            raise RuntimeError(f"GCS screenshot download failed: {exc}") from exc

