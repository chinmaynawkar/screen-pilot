"""
Load HTML templates from the templates directory.

Templates are resolved relative to this package so they work regardless
of the process working directory.
"""
from pathlib import Path

_TEMPLATES_DIR = Path(__file__).resolve().parent
_TIMESHEET_DEMO_PATH = _TEMPLATES_DIR / "timesheet_demo.html"


def get_timesheet_demo_html() -> str:
    """
    Return the full HTML for the professional timesheet demo page.

    Raises:
        FileNotFoundError: If the template file is missing.
    """
    if not _TIMESHEET_DEMO_PATH.exists():
        raise FileNotFoundError(f"Template not found: {_TIMESHEET_DEMO_PATH}")
    return _TIMESHEET_DEMO_PATH.read_text(encoding="utf-8")
