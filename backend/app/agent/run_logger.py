from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class AgentRunLogEntry:
    run_id: str
    session_id: str
    project_id: str | None
    current_step: str
    next_action: str
    requires_user_input: bool
    duration_ms: int
    tool_calls: list[str]
    trace: list[str]
    trace_summary: dict[str, Any]
    created_at: str


class AgentRunLogger:
    """Persist agent workflow runs for later inspection."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, entry: AgentRunLogEntry) -> None:
        payload = asdict(entry)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    @staticmethod
    def build_created_at() -> str:
        return datetime.now(timezone.utc).isoformat()
