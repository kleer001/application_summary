"""Build an authorization workbook from a release PDF that has no prior spreadsheet.

Same column set as a reconciled workbook, so sheets from different releases
concatenate. Every text value is a verbatim quote carrying the pages it came from.
Habitat area figures are written to the Extracted_ columns only; the canonical
HADD_ columns stay empty until a person confirms them.

Usage: build_new.py <ocr.txt> <segments.json> <out.xlsx> <source-pdf-name>
"""
import json, re, sys
import openpyxl
from openpyxl.styles import Font, Alignment
from openpyxl.utils import get_column_letter

from segment import load_pages, FILE_RX
from extract import extract, front_fields, seg_text

COLUMNS = [
    "Source_Part", "Source_File", "DFO_File_or_PATH", "Region", "Authorization_Date",
    "Authorization_Issue_Year", "Amendment_Date", "Amendment_Year", "Proponent",
    "Project_Name_or_Description", "Province", "Aquatic_Setting", "Project_Type",
    "Authorized_Impact_Summary", "HADD_Destruction_m2", "HADD_Alteration_m2",
    "HADD_Disturbance_m2", "HADD_Total_m2", "HADD_Other_Units", "Total_Habitat_Affected_m2",
    "Offsetting_Measures", "Offsetting_Required", "Offsetting_Provided", "Offsetting_Unit",
    "Offsetting_Required_Value", "Offsetting_Required_Unit",
    "Offsetting_Provided_Value", "Offsetting_Provided_Unit",
    "Habitat_Bank_Name", "Monitoring_Requirements", "Contingency_Measures",
    "Include_in_2021_Request", "QA_Flag", "Review_Notes", "Source_Reference_ID",
    "PDF_Page_Start", "PDF_Page_End", "Bates_Start", "Bates_End", "Source_Page_Anchor",
    "Record_Type", "Confidence", "Confidence_Basis", "Verification_Status",
    "Unverified_Reason", "Redaction_Exemptions", "Derived_Fields",
    "Extracted_HADD_Destruction_m2", "Extracted_HADD_Alteration_m2",
    "Extracted_HADD_Disturbance_m2", "Auto_Fill_Notes",
]

# Derived from the A-2020-02093 corpus, where the mapping holds without exception.
REGION = {
    "HPAC": "Pacific", "HCAA": "Central and Arctic", "HGLF": "Gulf",
    "HMAR": "Maritimes", "HNFL": "Newfoundland and Labrador", "HQUE": "Quebec",
}
REGION_PROVINCES = {
    "HPAC": {"British Columbia", "Yukon"},
    "HCAA": {"Ontario", "Alberta", "Manitoba", "Saskatchewan", "Nunavut",
             "Northwest Territories"},
    "HGLF": {"New Brunswick", "Prince Edward Island"},
    "HMAR": {"Nova Scotia"},
    "HNFL": {"Newfoundland and Labrador"},
    "HQUE": {"Quebec"},
}
PROVINCE_FIX = {
    "québec": "Quebec", "quebec": "Quebec", "on": "Ontario", "ont": "Ontario",
    "b.c.": "British Columbia", "bc": "British Columbia", "n.b.": "New Brunswick",
    "nb": "New Brunswick", "ns": "Nova Scotia", "pei": "Prince Edward Island",
    "yukon territory": "Yukon", "nwt": "Northwest Territories",
}

REDACTION_RX = re.compile(r"\bs\s*\.?\s*(1[3-9]|2[0-4])\s*\(\s*1\s*\)\s*(\(\s*[a-c]\s*\))?", re.I)
INFERRED = " (i)"

SETTING_WORDS = {
    "marine": ["marine", "harbour", "harbor", "intertidal", "subtidal", "tidal", "wharf",
               "port ", "seabed", "ocean", "havre", "quai", "maritime", "estran"],
    "freshwater": ["river", "lake", "stream", "creek", "brook", "drain", "pond", "watercourse",
                   "rivière", "riviere", "lac ", "ruisseau", "étang", "etang", "cours d'eau",
                   "fleuve", "tributary", "wetland", "marsh"],
}
TYPE_RULES = [
    (r"\bculvert|ponceau", "Road / culvert infrastructure"),
    (r"\bbridge\b|\bpont\b|passerelle", "Bridge / transportation infrastructure"),
    (r"dredg|dragage", "Dredging"),
    (r"pipeline|conduite|gazoduc|ol[ée]oduc", "Pipeline crossing"),
    (r"enrochement|bank stabiliz|stabilisation (?:de|des) berge|shoreline protection", "Bank stabilization"),
    (r"\bmine\b|mini[èe]re|mining|quarry|carri[èe]re|tailings", "Mine / mining"),
    (r"wharf|quai|harbour|harbor|marina|breakwater|brise-lame|boat launch", "Port / marine infrastructure"),
    (r"railway|chemin de fer|\brail\b", "Railway infrastructure"),
    (r"highway|autoroute|\broad\b|\broute\b", "Highway infrastructure"),
    (r"subdivision|residential|r[ée]sidentiel|lotissement", "Residential development"),
    (r"water intake|prise d'eau|aqueduc", "Water intake infrastructure"),
    (r"barrage|\bdam\b|digue", "Dam / water control"),
    (r"[ée]missaire|outfall|sewer|[ée]gout", "Outfall / wastewater"),
    (r"hydro|transmission line|ligne de transport", "Power infrastructure"),
]


def infer_setting(text):
    low = text.lower()
    m = sum(low.count(w) for w in SETTING_WORDS["marine"])
    f = sum(low.count(w) for w in SETTING_WORDS["freshwater"])
    if m == 0 and f == 0:
        return None
    if m and f and abs(m - f) <= max(1, 0.2 * max(m, f)):
        return "Estuarine / mixed" + INFERRED
    return ("Marine" if m > f else "Freshwater") + INFERRED


def infer_type(text):
    low = text.lower()
    for rx, label in TYPE_RULES:
        if re.search(rx, low):
            return label + INFERRED
    return None


def region_of(file_no):
    m = re.search(r"\d{2}-(H[A-Z]{3})-", str(file_no))
    return REGION.get(m.group(1)) if m else None


def redactions(pages, start, end):
    found = {re.sub(r"\s", "", m.group(0))
             for p in pages[start - 1:end] for m in REDACTION_RX.finditer(p)}
    return "; ".join(sorted(found)) or None


def anchor(sg):
    a = f"PDF pp. {sg['start']}-{sg['end']}"
    if sg.get("bates_start"):
        a += f" (Bates {sg['bates_start']:06d}-{sg['bates_end']:06d})"
    pe = sg.get("package_end")
    if pe and pe > sg["end"]:
        a += f"; attachments to p. {pe}"
    return a


def main(txt_path, segs_path, out_path, source_name):
    pages = load_pages(txt_path)
    segs = sorted(json.load(open(segs_path, encoding="utf-8")), key=lambda s: s["start"])

    by_file = {}
    for s in segs:
        by_file.setdefault(s["file_no"], []).append(s)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Authorization_Summary"
    ws.append(COLUMNS)
    idx = {h: i + 1 for i, h in enumerate(COLUMNS)}

    queue, mismatches = [], 0
    for s in segs:
        ex = extract(pages, s)
        fr = front_fields(pages, s)
        text = seg_text(pages, s)
        row = {}

        prov = fr.get("province")
        if prov:
            prov = PROVINCE_FIX.get(prov.strip().lower(), prov.strip())
        reg_code = re.search(r"\d{2}-(H[A-Z]{3})-", str(s["file_no"]))
        notes = [f"Row built from {source_name} at {anchor(s)}."]
        if reg_code and prov and reg_code.group(1) in REGION_PROVINCES:
            if prov not in REGION_PROVINCES[reg_code.group(1)]:
                notes.append(f"Province '{prov}' is outside the {reg_code.group(1)} region; check both.")
                mismatches += 1

        group = by_file.get(s["file_no"], [])
        is_amend = len(group) > 1 and s is not group[0]

        n_sections = ex["n_sections"]
        if str(s["file_no"]).startswith("Auth "):
            tier, basis = "tentative", "no legible file number; identified by authorisation number only"
        elif s.get("file_no_repaired"):
            tier, basis = "probable", "file number required OCR letter-for-digit repair"
        elif n_sections < 3:
            tier, basis = "probable", f"only {n_sections} numbered condition sections recognised"
        else:
            tier, basis = "confirmed", f"file number read from the page header; {n_sections} condition sections present"

        red = redactions(pages, s["start"], s["end"])
        prop = fr["proponent"]
        if prop and re.search(r"\b(?:you|we|dated|further to|thank)\b", prop, re.I):
            notes.append("Proponent did not parse as a name; this may be correspondence "
                         "rather than an authorization form.")
            tier, basis = "tentative", "proponent field did not parse as a name"
        row.update({
            "Source_File": source_name,
            "DFO_File_or_PATH": s["file_no"],
            "Region": region_of(s["file_no"]),
            "Proponent": fr["proponent"],
            "Project_Name_or_Description": fr["project"],
            "Province": prov,
            "Aquatic_Setting": infer_setting(text[:6000]),
            "Project_Type": infer_type(text[:6000]),
            "Authorized_Impact_Summary": ex["impact_summary"],
            "Total_Habitat_Affected_m2": ex["total_impact_m2"],
            "Offsetting_Measures": ex["offsetting"],
            "Monitoring_Requirements": ex["monitoring"],
            "Contingency_Measures": ex["contingency"],
            "PDF_Page_Start": s["start"], "PDF_Page_End": s["end"],
            "Bates_Start": s.get("bates_start"), "Bates_End": s.get("bates_end"),
            "Source_Page_Anchor": anchor(s), "Source_Reference_ID": anchor(s),
            "Record_Type": "amendment" if is_amend else "authorization",
            "Confidence": tier, "Confidence_Basis": basis,
            "Redaction_Exemptions": red,
            "Extracted_HADD_Destruction_m2": ex["hadd_sum"].get("destruction"),
            "Extracted_HADD_Alteration_m2": ex["hadd_sum"].get("alteration"),
            "Extracted_HADD_Disturbance_m2": ex["hadd_sum"].get("disruption"),
            "QA_Flag": "BUILT FROM PDF - no prior workbook to reconcile against",
            "Verification_Status": "unreconciled: no prior value to compare",
            "Auto_Fill_Notes": " ".join(notes),
        })
        ws.append([row.get(c) for c in COLUMNS])

        for label, key in (("HADD_Destruction_m2", "destruction"),
                           ("HADD_Alteration_m2", "alteration"),
                           ("HADD_Disturbance_m2", "disruption")):
            v = ex["hadd_sum"].get(key)
            if v is not None:
                queue.append([ws.max_row, s["file_no"], label, v,
                              ", ".join(f"{p:,.1f}" for p in (ex["hadd_parts"].get(key) or [])),
                              anchor(s), (ex["impact_summary"] or "")[:600]])

    q = wb.create_sheet("Numeric_Review_Queue")
    q.append(["Row", "DFO_File_or_PATH", "Column", "Extracted_Candidate",
              "Components_Found", "Source_Page_Anchor", "Source_Sentence"])
    for e in queue:
        q.append(e)

    ov = wb.create_sheet("Overview")
    conf = {}
    for r in range(2, ws.max_row + 1):
        k = ws.cell(row=r, column=idx["Confidence"]).value
        conf[k] = conf.get(k, 0) + 1
    ov.append(["Metric", "Value"])
    for k, v in [
        ("Source PDF", source_name),
        ("Pages", len(pages)),
        ("Authorizations found", sum(1 for r in range(2, ws.max_row + 1)
                                     if ws.cell(row=r, column=idx["Record_Type"]).value == "authorization")),
        ("Amendments found", sum(1 for r in range(2, ws.max_row + 1)
                                 if ws.cell(row=r, column=idx["Record_Type"]).value == "amendment")),
        ("Rows total", ws.max_row - 1),
        ("Confidence confirmed / probable / tentative",
         f"{conf.get('confirmed',0)} / {conf.get('probable',0)} / {conf.get('tentative',0)}"),
        ("Rows touching redactions", sum(1 for r in range(2, ws.max_row + 1)
                                         if ws.cell(row=r, column=idx["Redaction_Exemptions"]).value)),
        ("Region / province mismatches", mismatches),
        ("Figures queued for review", len(queue)),
        ("Note", "Built with no prior spreadsheet. Text columns are verbatim quotes from the "
                 "page range in Source_Page_Anchor. Habitat area figures appear only in the "
                 "Extracted_ columns; the canonical HADD_ columns are left empty for a person "
                 "to confirm from Numeric_Review_Queue."),
    ]:
        ov.append([k, v])

    for sheet, widths in ((ws, None), (q, (6, 26, 26, 18, 24, 34, 80)), (ov, (44, 90))):
        for c in sheet[1]:
            c.font = Font(bold=True)
        sheet.freeze_panes = "A2"
        if widths:
            for col, w in zip("ABCDEFG", widths):
                sheet.column_dimensions[col].width = w
    for name in ("DFO_File_or_PATH", "Proponent", "Project_Name_or_Description",
                 "Source_Page_Anchor", "Auto_Fill_Notes", "Confidence_Basis"):
        ws.column_dimensions[get_column_letter(idx[name])].width = 30
    for r in range(2, ov.max_row + 1):
        ov.cell(row=r, column=2).alignment = Alignment(wrap_text=True, vertical="top")

    wb.save(out_path)
    print(f"{source_name}: {ws.max_row-1} rows "
          f"({conf.get('confirmed',0)} confirmed, {conf.get('probable',0)} probable, "
          f"{conf.get('tentative',0)} tentative), {len(queue)} figures queued, "
          f"{mismatches} region mismatches -> {out_path}")


if __name__ == "__main__":
    main(*sys.argv[1:5])
