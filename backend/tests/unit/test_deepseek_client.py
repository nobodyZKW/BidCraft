from __future__ import annotations

import json

import pytest

from app.llm.deepseek_client import DeepSeekClient
from app.llm.logger import LLMCallLogger
from app.llm.types import StructuredLLMRequest
from app.schemas.json_schemas import EXTRACTION_SCHEMA


@pytest.mark.allow_real_llm_client
def test_invoke_structured_logs_failure_when_api_key_missing(tmp_path) -> None:
    client = DeepSeekClient()
    client.api_key = ""
    client.logger = LLMCallLogger(tmp_path / "llm_calls.jsonl")

    result = client.invoke_structured(
        StructuredLLMRequest(
            task_name="test.extraction",
            task_prompt="extract demo payload",
            schema=EXTRACTION_SCHEMA,
            system_prompt="return json",
        )
    )

    assert result is None
    rows = (tmp_path / "llm_calls.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert rows
    payload = json.loads(rows[-1])
    assert payload["task_name"] == "test.extraction"
    assert payload["success"] is False
    assert payload["error"] == "missing_api_key"
