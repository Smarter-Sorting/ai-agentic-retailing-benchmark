import re
import zipfile
import xml.etree.ElementTree as ET


_NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_CELL_REF_RE = re.compile(r"([A-Z]+)([0-9]+)")
def load_product_ground_truth(path):
    # Load ground-truth rows keyed by sku_id with comma-separated values.
    rows = _load_xlsx_rows(path)
    if not rows:
        return {}
    ground_truth = {}
    for row in rows:
        sku_id = (row.get("sku_id") or "").strip()
        if not sku_id:
            continue
        values = []
        for key, value in row.items():
            if key == "sku_id":
                continue
            if value is None:
                continue
            text = str(value).strip()
            if not text:
                continue
            values.append(text)
        ground_truth[sku_id] = ", ".join(values)
    return ground_truth


def _load_xlsx_rows(path):
    # Load rows from the first worksheet as dicts keyed by the header row.
    try:
        with zipfile.ZipFile(path) as zf:
            shared_strings = _read_shared_strings(zf)
            sheet_xml = _read_first_sheet(zf)
    except FileNotFoundError:
        return []

    rows = _parse_sheet_rows(sheet_xml, shared_strings)
    if not rows:
        return []

    header = rows[0]
    data_rows = rows[1:]
    result = []
    for row in data_rows:
        row_dict = {}
        for idx, name in enumerate(header):
            if not name:
                continue
            row_dict[name] = row[idx] if idx < len(row) else ""
        result.append(row_dict)
    return result


def _read_shared_strings(zf):
    # Collect shared strings for resolving string cell references.
    try:
        shared_xml = zf.read("xl/sharedStrings.xml")
    except KeyError:
        return []

    root = ET.fromstring(shared_xml)
    strings = []
    for si in root.findall("a:si", _NS):
        texts = []
        for t in si.findall(".//a:t", _NS):
            texts.append(t.text or "")
        strings.append("".join(texts))
    return strings


def _read_first_sheet(zf):
    # XLSX uses workbook.xml to map sheet IDs to files.
    workbook_xml = zf.read("xl/workbook.xml")
    workbook_root = ET.fromstring(workbook_xml)
    sheet = workbook_root.find("a:sheets/a:sheet", _NS)
    if sheet is None:
        raise ValueError("No worksheets found in XLSX.")

    sheet_id = sheet.attrib.get(
        "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    )
    rels_xml = zf.read("xl/_rels/workbook.xml.rels")
    rels_root = ET.fromstring(rels_xml)
    for rel in rels_root:
        if rel.attrib.get("Id") == sheet_id:
            target = rel.attrib.get("Target")
            break
    else:
        raise ValueError("Worksheet relationship not found.")

    sheet_path = "xl/" + target.lstrip("/")
    return zf.read(sheet_path)


def _parse_sheet_rows(sheet_xml, shared_strings):
    # Build dense row arrays from sparse cell entries.
    root = ET.fromstring(sheet_xml)
    rows = []
    max_col = 0
    raw_rows = []

    for row in root.findall(".//a:sheetData/a:row", _NS):
        cells = {}
        for cell in row.findall("a:c", _NS):
            ref = cell.attrib.get("r")
            if not ref:
                continue
            match = _CELL_REF_RE.match(ref)
            if not match:
                continue
            col_letters = match.group(1)
            col_index = _col_to_index(col_letters)
            max_col = max(max_col, col_index)
            cells[col_index] = _read_cell_value(cell, shared_strings)
        raw_rows.append(cells)

    for cells in raw_rows:
        row_vals = [""] * max_col
        for col_index, value in cells.items():
            row_vals[col_index - 1] = value
        rows.append(row_vals)
    return rows


def _read_cell_value(cell, shared_strings):
    # Decode cell values, handling shared and inline strings.
    cell_type = cell.attrib.get("t")
    value_node = cell.find("a:v", _NS)
    if cell_type == "s":
        if value_node is None or value_node.text is None:
            return ""
        return shared_strings[int(value_node.text)]
    if cell_type == "inlineStr":
        text_node = cell.find(".//a:t", _NS)
        return text_node.text if text_node is not None else ""
    if value_node is None or value_node.text is None:
        return ""
    return value_node.text


def _col_to_index(col_letters):
    # Convert Excel column letters (e.g. "AB") to 1-based index.
    index = 0
    for ch in col_letters:
        index = index * 26 + (ord(ch) - 64)
    return index
