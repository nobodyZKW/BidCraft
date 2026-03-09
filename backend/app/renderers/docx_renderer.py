from __future__ import annotations

import zipfile
from pathlib import Path


def _xml_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def write_simple_docx(content: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    paragraphs = [line for line in content.splitlines() if line.strip()] or [""]
    paragraph_xml = "".join(
        f"<w:p><w:r><w:t xml:space='preserve'>{_xml_escape(line)}</w:t></w:r></w:p>"
        for line in paragraphs
    )
    document_xml = (
        "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
        "<w:document xmlns:wpc='http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas' "
        "xmlns:mc='http://schemas.openxmlformats.org/markup-compatibility/2006' "
        "xmlns:o='urn:schemas-microsoft-com:office:office' "
        "xmlns:r='http://schemas.openxmlformats.org/officeDocument/2006/relationships' "
        "xmlns:m='http://schemas.openxmlformats.org/officeDocument/2006/math' "
        "xmlns:v='urn:schemas-microsoft-com:vml' "
        "xmlns:wp14='http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing' "
        "xmlns:wp='http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing' "
        "xmlns:w10='urn:schemas-microsoft-com:office:word' "
        "xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main' "
        "xmlns:w14='http://schemas.microsoft.com/office/word/2010/wordml' "
        "xmlns:wpg='http://schemas.microsoft.com/office/word/2010/wordprocessingGroup' "
        "xmlns:wpi='http://schemas.microsoft.com/office/word/2010/wordprocessingInk' "
        "xmlns:wne='http://schemas.microsoft.com/office/word/2006/wordml' "
        "xmlns:wps='http://schemas.microsoft.com/office/word/2010/wordprocessingShape' mc:Ignorable='w14 wp14'>"
        f"<w:body>{paragraph_xml}<w:sectPr/></w:body></w:document>"
    )

    content_types = (
        "<?xml version='1.0' encoding='UTF-8'?>"
        "<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'>"
        "<Default Extension='rels' ContentType='application/vnd.openxmlformats-package.relationships+xml'/>"
        "<Default Extension='xml' ContentType='application/xml'/>"
        "<Override PartName='/word/document.xml' "
        "ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml'/>"
        "</Types>"
    )
    rels = (
        "<?xml version='1.0' encoding='UTF-8'?>"
        "<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'>"
        "<Relationship Id='rId1' "
        "Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument' "
        "Target='word/document.xml'/>"
        "</Relationships>"
    )

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", content_types)
        docx.writestr("_rels/.rels", rels)
        docx.writestr("word/document.xml", document_xml)
    return output_path
