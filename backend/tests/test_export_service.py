from __future__ import annotations

from pathlib import Path

from app.services.export_service import ExportService


def test_export_service_writes_docx_and_pdf(tmp_path: Path) -> None:
    service = ExportService(export_dir=tmp_path)
    content = "BidCraft AI Export Test"

    docx_path = service.export(
        project_name="服务器采购项目",
        rendered_content=content,
        doc_type="tender",
        version=1,
        fmt="docx",
        mode="draft",
    )
    pdf_path = service.export(
        project_name="服务器采购项目",
        rendered_content=content,
        doc_type="tender",
        version=1,
        fmt="pdf",
        mode="formal",
    )

    assert docx_path.exists()
    assert pdf_path.exists()
    assert docx_path.suffix == ".docx"
    assert pdf_path.suffix == ".pdf"
    assert docx_path.stat().st_size > 0
    assert pdf_path.stat().st_size > 0
