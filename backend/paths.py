"""Centralized path resolution — all data/template paths go through here."""
from pathlib import Path

# Root del progetto = parent di backend/
_BACKEND_DIR = Path(__file__).parent
_PROJECT_ROOT = _BACKEND_DIR.parent


def get_data_dir() -> Path:
    """Return absolute path to the data/ directory, creating it if needed."""
    d = _PROJECT_ROOT / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_template_dir() -> Path:
    """Return absolute path to backend/templates/."""
    return _BACKEND_DIR / "templates"


def data_file(filename: str) -> Path:
    """Return absolute path to a file inside data/."""
    return get_data_dir() / filename
