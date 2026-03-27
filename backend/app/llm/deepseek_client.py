from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from typing import Any

from app.core.settings import settings
from app.llm.logger import LLMCallLogEntry, LLMCallLogger
from app.llm.types import StructuredLLMRequest, TextLLMRequest


class DeepSeekClient:
    def __init__(self) -> None:
        self.api_key = settings.deepseek_api_key
        self.base_url = settings.deepseek_base_url.rstrip("/")
        self.model = settings.deepseek_model
        self.timeout_seconds = settings.request_timeout_seconds
        self.logger = LLMCallLogger(settings.runtime_dir / "llm_calls.jsonl")

    @staticmethod
    def _extract_json_from_text(content: str) -> dict[str, Any]:
        content = content.strip()
        fenced = re.search(r"```json\s*(\{.*\})\s*```", content, re.DOTALL)
        if fenced:
            return json.loads(fenced.group(1))

        braces = re.search(r"(\{.*\})", content, re.DOTALL)
        if braces:
            return json.loads(braces.group(1))

        return json.loads(content)

    @staticmethod
    def _format_schema_prompt(schema: dict[str, Any]) -> str:
        return json.dumps(schema, ensure_ascii=False)

    def _chat(self, messages: list[dict[str, str]]) -> str:
        url = f"{self.base_url}/chat/completions"
        body = {
            "model": self.model,
            "temperature": 0.1,
            "messages": messages,
        }
        req = urllib.request.Request(
            url=url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            return payload["choices"][0]["message"]["content"]

    def _log(
        self,
        *,
        task_name: str,
        success: bool,
        duration_ms: int,
        response_format: str,
        metadata: dict[str, Any],
        error: str | None = None,
    ) -> None:
        self.logger.log(
            LLMCallLogEntry(
                task_name=task_name,
                provider="deepseek",
                model=self.model,
                success=success,
                duration_ms=duration_ms,
                response_format=response_format,
                error=error,
                metadata=metadata,
            )
        )

    def invoke_text(self, request: TextLLMRequest) -> str | None:
        if not self.api_key:
            self._log(
                task_name=request.task_name,
                success=False,
                duration_ms=0,
                response_format="text",
                metadata=request.metadata,
                error="missing_api_key",
            )
            return None

        messages = [
            {"role": "system", "content": request.system_prompt},
            {"role": "user", "content": request.user_prompt},
        ]

        last_error: str | None = None
        started = time.perf_counter()
        for _ in range(max(1, request.max_retries)):
            try:
                content = self._chat(messages)
                self._log(
                    task_name=request.task_name,
                    success=True,
                    duration_ms=int((time.perf_counter() - started) * 1000),
                    response_format="text",
                    metadata=request.metadata,
                )
                return content
            except (
                urllib.error.URLError,
                urllib.error.HTTPError,
                json.JSONDecodeError,
                KeyError,
            ) as exc:
                last_error = str(exc)

        self._log(
            task_name=request.task_name,
            success=False,
            duration_ms=int((time.perf_counter() - started) * 1000),
            response_format="text",
            metadata=request.metadata,
            error=last_error,
        )
        return None

    def invoke_structured(self, request: StructuredLLMRequest) -> dict[str, Any] | None:
        schema_str = self._format_schema_prompt(request.schema)
        user_prompt = (
            "Return valid JSON only.\n"
            f"JSON schema:\n{schema_str}\n"
            f"Task:\n{request.task_prompt}\n"
        )
        content = self.invoke_text(
            TextLLMRequest(
                task_name=request.task_name,
                system_prompt=request.system_prompt,
                user_prompt=user_prompt,
                max_retries=request.max_retries,
                metadata={**request.metadata, "response_schema_keys": list(request.schema.keys())},
            )
        )
        if content is None:
            return None
        try:
            return self._extract_json_from_text(content)
        except json.JSONDecodeError as exc:
            self._log(
                task_name=f"{request.task_name}.parse",
                success=False,
                duration_ms=0,
                response_format="structured_json",
                metadata=request.metadata,
                error=str(exc),
            )
            return None

    def extract_structured_json(
        self,
        raw_input_text: str,
        schema: dict[str, Any],
    ) -> dict[str, Any] | None:
        task_prompt = (
            "Task A: Extract procurement requirements.\n"
            "Task B: Fill missing_fields and clarification_questions.\n"
            f"Raw requirement text:\n{raw_input_text}\n"
        )
        return self.invoke_structured(
            StructuredLLMRequest(
                task_name="extraction",
                task_prompt=task_prompt,
                schema=schema,
                system_prompt=(
                    "You are a procurement analyst. Return JSON only, no markdown. "
                    "Output must strictly conform to provided JSON schema."
                ),
                metadata={"source": "compat.extract_structured_json"},
            )
        )

    def generate_structured_json(
        self,
        *,
        task_prompt: str,
        schema: dict[str, Any],
        system_prompt: str,
    ) -> dict[str, Any] | None:
        return self.invoke_structured(
            StructuredLLMRequest(
                task_name="structured_generation",
                task_prompt=task_prompt,
                schema=schema,
                system_prompt=system_prompt,
                metadata={"source": "compat.generate_structured_json"},
            )
        )
