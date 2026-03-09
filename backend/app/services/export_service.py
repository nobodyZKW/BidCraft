from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from app.renderers.docx_renderer import write_simple_docx
from app.renderers.pdf_renderer import write_simple_pdf


class ExportService:
    def __init__(self, export_dir: Path):
        self.export_dir = export_dir

    @staticmethod
    def _safe_name(text: str) -> str:
        sanitized = re.sub(r"[\\/:*?\"<>|]+", "_", text.strip())
        return sanitized or "untitled_project"

    def export(
        self,
        project_name: str,
        rendered_content: str,
        doc_type: str,
        version: int,
        fmt: str,
        mode: str,
    ) -> Path:
        today = date.today().strftime("%Y-%m-%d")
        filename = f"{self._safe_name(project_name)}_{doc_type}_v{version}_{today}.{fmt}"
        output_path = self.export_dir / filename

        content = rendered_content
        if mode == "draft":
            content = "[DRAFT WATERMARK]\n" + rendered_content

        if fmt == "docx":
            return write_simple_docx(content, output_path)
        if fmt == "pdf":
            return write_simple_pdf(content, output_path)
        raise ValueError(f"Unsupported export format: {fmt}")
