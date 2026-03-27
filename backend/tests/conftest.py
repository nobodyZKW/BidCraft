from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest


ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


from app.api.dependencies import (  # noqa: E402
    get_agent_workflow_runner,
    get_knowledge_retrieval_service,
    get_llm_client,
    get_project_service,
)
from app.core.settings import settings  # noqa: E402
from app.llm.deepseek_client import DeepSeekClient  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_runtime() -> None:
    settings.runtime_dir.mkdir(parents=True, exist_ok=True)
    for file in settings.runtime_dir.glob("*.json"):
        file.unlink(missing_ok=True)
    for file in settings.runtime_dir.glob("*.jsonl"):
        file.unlink(missing_ok=True)
    settings.export_dir.mkdir(parents=True, exist_ok=True)
    for file in settings.export_dir.glob("*"):
        if file.is_file():
            file.unlink()
        elif file.is_dir():
            shutil.rmtree(file)
    get_project_service.cache_clear()
    get_agent_workflow_runner.cache_clear()
    get_knowledge_retrieval_service.cache_clear()
    get_llm_client.cache_clear()
    yield


@pytest.fixture(autouse=True)
def _mock_llm(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if request.node.get_closest_marker("allow_real_llm_client"):
        return
    monkeypatch.setattr(
        DeepSeekClient,
        "invoke_structured",
        lambda self, request: None,
    )
