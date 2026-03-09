from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest


ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


from app.api.dependencies import get_project_service  # noqa: E402
from app.core.settings import settings  # noqa: E402
from app.llm.deepseek_client import DeepSeekClient  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_runtime() -> None:
    settings.runtime_dir.mkdir(parents=True, exist_ok=True)
    for file in settings.runtime_dir.glob("*.json"):
        file.unlink(missing_ok=True)
    settings.export_dir.mkdir(parents=True, exist_ok=True)
    for file in settings.export_dir.glob("*"):
        if file.is_file():
            file.unlink()
        elif file.is_dir():
            shutil.rmtree(file)
    get_project_service.cache_clear()
    yield


@pytest.fixture(autouse=True)
def _mock_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        DeepSeekClient,
        "extract_structured_json",
        lambda self, raw_input_text, schema: None,
    )
