from __future__ import annotations

from typing import Any

from app.repositories.json_file_store import JsonFileStore


class AgentStateRepository:
    """Persistence for agent graph state keyed by project_id."""

    def __init__(self, runtime_dir):
        self.store = JsonFileStore(runtime_dir / "agent_states.json")

    def get_state(self, project_id: str) -> dict[str, Any] | None:
        payload = self.store.load()
        item = payload.get(project_id)
        if not item:
            return None
        if not isinstance(item, dict):
            return None
        return item

    def save_state(self, project_id: str, state: dict[str, Any]) -> None:
        payload = self.store.load()
        payload[project_id] = state
        self.store.save(payload)

