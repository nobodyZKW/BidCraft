from __future__ import annotations

from pathlib import Path


def _pdf_escape(text: str) -> str:
    cleaned = "".join(ch if 32 <= ord(ch) <= 126 else "?" for ch in text)
    return cleaned.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_simple_pdf(content: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [line for line in content.splitlines() if line.strip()][:80] or [""]

    text_commands = ["BT", "/F1 11 Tf", "50 780 Td", "14 TL"]
    for line in lines:
        text_commands.append(f"({_pdf_escape(line)}) Tj")
        text_commands.append("T*")
    text_commands.append("ET")
    stream_text = "\n".join(text_commands).encode("latin-1", errors="replace")

    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objects.append(
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
    )
    objects.append(
        f"<< /Length {len(stream_text)} >>\nstream\n".encode("latin-1")
        + stream_text
        + b"\nendstream"
    )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    offsets = []
    pdf = bytearray(header)

    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{idx} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            "trailer\n"
            f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            "startxref\n"
            f"{xref_start}\n"
            "%%EOF\n"
        ).encode("ascii")
    )

    output_path.write_bytes(bytes(pdf))
    return output_path
