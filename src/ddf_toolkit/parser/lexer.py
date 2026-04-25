"""DDF CSV lexer — reads raw CSV into section-tagged rows."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from pathlib import Path

import chardet


@dataclass
class DDFRow:
    line_number: int
    section: str
    cells: list[str]


class DDFSyntaxError(Exception):
    def __init__(self, message: str, line: int | None = None) -> None:
        self.line = line
        super().__init__(f"Line {line}: {message}" if line else message)


def detect_encoding(raw: bytes) -> str:
    """Detect file encoding via BOM or chardet."""
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    if raw.startswith(b"\xff\xfe"):
        return "utf-16-le"
    if raw.startswith(b"\xfe\xff"):
        return "utf-16-be"
    result = chardet.detect(raw)
    encoding = result.get("encoding") or "utf-8"
    if encoding.lower() in ("ascii", "windows-1252", "iso-8859-1"):
        return "cp1252"
    return encoding


def lex_ddf(path: Path) -> list[DDFRow]:
    """Lex a DDF CSV file into section-tagged rows."""
    raw = path.read_bytes()
    encoding = detect_encoding(raw)
    text = raw.decode(encoding)

    rows: list[DDFRow] = []
    current_section = ""

    reader = csv.reader(io.StringIO(text), delimiter=";")
    for line_number, cells in enumerate(reader, start=1):
        if not cells or all(c.strip() == "" for c in cells):
            continue

        first = cells[0].strip()

        # Comment lines
        if first.startswith("#"):
            continue

        # Section header
        if first.startswith("*"):
            # Normalize alternative section names (DeviceLib.pdf p.5)
            section_aliases = {
                "*PREPROCESS": "*READ",
                "*ONCHANGE": "*WRITE",
            }
            current_section = section_aliases.get(first, first)
            rows.append(DDFRow(line_number=line_number, section=current_section, cells=cells))
            continue

        if not current_section:
            continue

        rows.append(DDFRow(line_number=line_number, section=current_section, cells=cells))

    return rows
