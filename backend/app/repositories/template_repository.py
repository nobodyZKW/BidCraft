from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class TemplateRepository:
    def __init__(self, template_file: Path):
        self.template_file = template_file

    def load(self) -> dict[str, Any]:
        if not self.template_file.exists():
            return {"sections": [], "rules": []}
        return json.loads(self.template_file.read_text(encoding="utf-8"))
