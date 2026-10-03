"""Enough xlsx to read a spreadsheet, with no dependency.

The environment has no openpyxl and installation is locked down, and the files are ordinary zipped
XML, so a small reader is cheaper than a dependency. It reads the shared string table, maps sheet names
to their part, and yields rows as lists.

It is deliberately narrow: no formulas, no styles, no dates as serial numbers. If a cell holds a
formula result, the cached value is used.
"""
from __future__ import annotations

import re
import zipfile
from xml.etree import ElementTree as ET

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _text(elem) -> str:
    return "".join(node.text or "" for node in elem.iter() if node.tag.endswith("}t"))


def shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    out: list[str] = []
    for _, elem in ET.iterparse(archive.open("xl/sharedStrings.xml"), events=("end",)):
        if elem.tag.endswith("}si"):
            out.append(_text(elem))
            elem.clear()
    return out


def sheet_parts(archive: zipfile.ZipFile) -> dict[str, str]:
    """Sheet name to the part that holds it, resolved through the workbook relationships."""
    workbook = archive.read("xl/workbook.xml").decode("utf-8", "ignore")
    wanted = dict(re.findall(r'<sheet name="([^"]+)"[^>]*r:id="(rId\d+)"', workbook))
    rels = archive.read("xl/_rels/workbook.xml.rels").decode("utf-8", "ignore")
    targets = dict(re.findall(r'Id="(rId\d+)"[^>]*Target="([^"]+)"', rels))
    parts: dict[str, str] = {}
    for name, rid in wanted.items():
        target = targets.get(rid, "")
        if not target:
            continue
        parts[name] = "xl/" + target.lstrip("/").replace("xl/", "", 1)
    return parts


def rows(archive: zipfile.ZipFile, part: str, shared: list[str]):
    """Yield one list per spreadsheet row, cells in column order."""
    for _, elem in ET.iterparse(archive.open(part), events=("end",)):
        if not elem.tag.endswith("}row"):
            continue
        cells: list[str] = []
        for cell in elem:
            if not cell.tag.endswith("}c"):
                continue
            value = cell.find(f"{NS}v")
            if cell.get("t") == "s" and value is not None and value.text is not None:
                cells.append(shared[int(value.text)])
            elif value is not None and value.text is not None:
                cells.append(value.text)
            else:
                cells.append(_text(cell))
        elem.clear()
        yield cells


def read_sheet(path, sheet_name: str) -> list[list[str]]:
    with zipfile.ZipFile(path) as archive:
        parts = sheet_parts(archive)
        if sheet_name not in parts:
            raise KeyError(f"{sheet_name} is not in {path}: found {sorted(parts)}")
        return list(rows(archive, parts[sheet_name], shared_strings(archive)))


def read_sheets(path, sheet_names) -> dict[str, list[list[str]]]:
    """All requested sheets in one pass over the archive, which matters at twelve megabytes a file."""
    with zipfile.ZipFile(path) as archive:
        parts = sheet_parts(archive)
        shared = shared_strings(archive)
        return {name: list(rows(archive, parts[name], shared))
                for name in sheet_names if name in parts}


def find_header(sheet: list[list[str]], marker: str = "Plant ID") -> int:
    """The row that carries the column names. The sheets open with a title and a blank row."""
    for index, row in enumerate(sheet[:12]):
        if any(cell.strip() == marker for cell in row):
            return index
    raise ValueError(f"no header row with {marker!r} in the first twelve rows")
