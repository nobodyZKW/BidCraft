from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class RuleRepository:
    def __init__(self, rule_file: Path):
        self.rule_file = rule_file

    def load_all(self) -> list[dict[str, Any]]:
        if not self.rule_file.exists():
            return []
        return list(json.loads(self.rule_file.read_text(encoding="utf-8")))
