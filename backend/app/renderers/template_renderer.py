from __future__ import annotations

import html
import re
from datetime import date
from typing import Any

from app.models.domain import Clause
from app.repositories.template_repository import TemplateRepository


PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


class TemplateRenderer:
    def __init__(self, template_repository: TemplateRepository):
        self.template_repository = template_repository

    @staticmethod
    def _format_value(field: str, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, list):
            return "；".join(str(item) for item in value)
        if field.endswith("_amount"):
            try:
                return f"{float(value):,.2f}"
            except (TypeError, ValueError):
                return str(value)
        if field.endswith("_date"):
            if isinstance(value, date):
                return value.strftime("%Y-%m-%d")
        return str(value)

    def _apply_placeholders(
        self,
        text: str,
        structured_data: dict[str, Any],
    ) -> tuple[str, list[str]]:
        unresolved: list[str] = []

        def _replace(match: re.Match[str]) -> str:
            key = match.group(1)
            raw_value = structured_data.get(key)
            if raw_value is None or raw_value == "":
                unresolved.append(key)
                return f"TODO({key})"
            return self._format_value(key, raw_value)

        output = PLACEHOLDER_PATTERN.sub(_replace, text)
        return output, unresolved

    @staticmethod
    def _is_rule_hit(when: dict[str, Any], data: dict[str, Any]) -> bool:
        for key, expected in when.items():
            if str(data.get(key)) != str(expected):
                return False
        return True

    def render(
        self,
        structured_data: dict[str, Any],
        selected_clauses: list[Clause],
    ) -> tuple[str, str, list[str], list[str]]:
        config = self.template_repository.load()
        sections_by_id = {item["id"]: item for item in config.get("sections", [])}

        included_section_ids: list[str] = []
        for rule in config.get("rules", []):
            when = rule.get("when", {})
            include = rule.get("include", [])
            if self._is_rule_hit(when, structured_data):
                for section_id in include:
                    if section_id not in included_section_ids:
                        included_section_ids.append(section_id)

        # keep stable output for preview and export
        included_section_ids = [sid for sid in included_section_ids if sid in sections_by_id]

        unresolved: list[str] = []
        output_parts: list[str] = []
        used_clause_ids: list[str] = [clause.clause_id for clause in selected_clauses]

        for section_id in included_section_ids:
            section = sections_by_id[section_id]
            content = section.get("content", "")
            filled, section_unresolved = self._apply_placeholders(content, structured_data)
            unresolved.extend(section_unresolved)
            output_parts.append(f"# {section.get('title', section_id)}\n{filled}")

        if selected_clauses:
            output_parts.append("# 合同专用条款")
            for clause in selected_clauses:
                clause_filled, clause_unresolved = self._apply_placeholders(
                    clause.content_template, structured_data
                )
                unresolved.extend(clause_unresolved)
                output_parts.append(
                    f"## {clause.clause_name} ({clause.clause_id}/{clause.version})\n{clause_filled}"
                )

        rendered_text = "\n\n".join(output_parts).strip()
        preview_html = "<html><body><pre>{}</pre></body></html>".format(
            html.escape(rendered_text)
        )
        unresolved_unique = sorted(set(unresolved))
        return rendered_text, preview_html, unresolved_unique, used_clause_ids
