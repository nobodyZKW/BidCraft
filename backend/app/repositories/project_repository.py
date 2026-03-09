from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.models.domain import (
    AuditEvent,
    DocumentVersion,
    Project,
    ProjectStatus,
    RequirementSnapshot,
)
from app.repositories.json_file_store import JsonFileStore


class ProjectRepository:
    def __init__(self, runtime_dir: Path):
        self.projects_store = JsonFileStore(runtime_dir / "projects.json")
        self.snapshots_store = JsonFileStore(runtime_dir / "snapshots.json")
        self.documents_store = JsonFileStore(runtime_dir / "documents.json")
        self.audit_store = JsonFileStore(runtime_dir / "audit_logs.json")

    @staticmethod
    def _next_id(prefix: str) -> str:
        return f"{prefix}_{uuid4().hex[:10]}"

    def create_project(self, project_name: str, department: str, created_by: str) -> Project:
        projects = self.projects_store.load()
        project = Project(
            project_id=self._next_id("p"),
            project_name=project_name,
            department=department,
            created_by=created_by,
        )
        projects[project.project_id] = project.model_dump(mode="json")
        self.projects_store.save(projects)
        return project

    def get_project(self, project_id: str) -> Project | None:
        projects = self.projects_store.load()
        item = projects.get(project_id)
        if not item:
            return None
        return Project.model_validate(item)

    def update_project_status(self, project_id: str, status: ProjectStatus) -> Project:
        projects = self.projects_store.load()
        item = projects.get(project_id)
        if not item:
            raise KeyError(f"Project not found: {project_id}")

        item["status"] = status.value
        item["updated_at"] = datetime.now(timezone.utc).isoformat()
        projects[project_id] = item
        self.projects_store.save(projects)
        return Project.model_validate(item)

    def save_snapshot(
        self,
        project_id: str,
        raw_input_text: str,
        structured_data: dict[str, Any],
        missing_fields: list[str],
    ) -> RequirementSnapshot:
        snapshots = self.snapshots_store.load()
        current_versions = [
            payload["version"]
            for payload in snapshots.values()
            if payload["project_id"] == project_id
        ]
        snapshot = RequirementSnapshot(
            snapshot_id=self._next_id("snap"),
            project_id=project_id,
            raw_input_text=raw_input_text,
            structured_data=structured_data,
            missing_fields=missing_fields,
            version=max(current_versions, default=0) + 1,
        )
        snapshots[snapshot.snapshot_id] = snapshot.model_dump(mode="json")
        self.snapshots_store.save(snapshots)
        return snapshot

    def get_latest_snapshot(self, project_id: str) -> RequirementSnapshot | None:
        snapshots = self.snapshots_store.load()
        items = [
            RequirementSnapshot.model_validate(payload)
            for payload in snapshots.values()
            if payload["project_id"] == project_id
        ]
        if not items:
            return None
        return sorted(items, key=lambda x: x.version, reverse=True)[0]

    def save_document_version(
        self,
        project_id: str,
        rendered_content: str,
        used_clause_ids: list[str],
        risk_result: dict[str, Any],
        export_status: str,
        file_urls: dict[str, str] | None = None,
    ) -> DocumentVersion:
        documents = self.documents_store.load()
        doc = DocumentVersion(
            doc_version_id=self._next_id("dv"),
            project_id=project_id,
            rendered_content=rendered_content,
            used_clause_ids=used_clause_ids,
            risk_result=risk_result,
            export_status=export_status,
            file_urls=file_urls or {},
        )
        documents[doc.doc_version_id] = doc.model_dump(mode="json")
        self.documents_store.save(documents)
        return doc

    def get_latest_document(self, project_id: str) -> DocumentVersion | None:
        documents = self.documents_store.load()
        items = [
            DocumentVersion.model_validate(payload)
            for payload in documents.values()
            if payload["project_id"] == project_id
        ]
        if not items:
            return None
        return sorted(items, key=lambda x: x.created_at, reverse=True)[0]

    def count_documents(self, project_id: str) -> int:
        documents = self.documents_store.load()
        return sum(
            1 for payload in documents.values() if payload.get("project_id") == project_id
        )

    def log_event(
        self,
        operator_id: str,
        project_id: str,
        action: str,
        before_snapshot: dict[str, Any],
        after_snapshot: dict[str, Any],
    ) -> AuditEvent:
        logs = self.audit_store.load()
        event = AuditEvent(
            operator_id=operator_id,
            project_id=project_id,
            action=action,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
        )
        event_id = self._next_id("log")
        logs[event_id] = event.model_dump(mode="json")
        self.audit_store.save(logs)
        return event
