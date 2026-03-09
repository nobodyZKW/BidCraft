from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any

from app.core.settings import settings


class DeepSeekClient:
    def __init__(self) -> None:
        self.api_key = settings.deepseek_api_key
        self.base_url = settings.deepseek_base_url.rstrip("/")
        self.model = settings.deepseek_model
        self.timeout_seconds = settings.request_timeout_seconds

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

    def extract_structured_json(
        self,
        raw_input_text: str,
        schema: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not self.api_key:
            return None

        schema_str = json.dumps(schema, ensure_ascii=False)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a procurement analyst. Return JSON only, no markdown. "
                    "Output must strictly conform to provided JSON schema."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Task A: Extract procurement requirements.\n"
                    "Task B: Fill missing_fields and clarification_questions.\n"
                    f"JSON schema:\n{schema_str}\n"
                    f"Raw requirement text:\n{raw_input_text}\n"
                ),
            },
        ]
        try:
            content = self._chat(messages)
            return self._extract_json_from_text(content)
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, KeyError):
            return None
