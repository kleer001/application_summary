"""Second pass over the workbook: amendments as their own rows, inferred
classifications, verification notes, and a cell-level Discrepancies sheet.

Runs after build_v2.py. Values already in the workbook are never overwritten;
where an extracted figure differs it is recorded alongside, not substituted.
"""
import json, re, sys
import openpyxl
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

from segment import load_pages, FILE_RX, norm_file
from extract import extract, front_fields, seg_text

XLSX = "/home/menser/Dropbox/BIZ/from_stantec/A-2020-02093-MRV-FINAL_pdf/DFO_2021_FAA_offsetting_summary_WORKING_v2.xlsx"

NEW_COLS = [
    "Record_Type", "Confidence", "Confidence_Basis", "Verification_Status",
    "Unverified_Reason", "Redaction_Exemptions", "Derived_Fields",
    "Extracted_HADD_Destruction_m2", "Extracted_HADD_Alteration_m2",
    "Extracted_HADD_Disturbance_m2",
]

INFERRED = " (i)"          # marks a value reasoned from the text, not quoted from it

REDACTION_RX = re.compile(r"\bs\s*\.?\s*(1[3-9]|2[0-4])\s*\(\s*1\s*\)\s*(\(\s*[a-c]\s*\))?", re.I)

PROVINCE_FIX = {
    "québec": "Quebec", "quebec": "Quebec", "on": "Ontario", "ont": "Ontario",
    "b.c.": "British Columbia", "bc": "British Columbia", "n.b.": "New Brunswick",
    "nb": "New Brunswick", "ns": "Nova Scotia", "pei": "Prince Edward Island",
}

SETTING_WORDS = {
    "marine": ["marine", "harbour", "harbor", "intertidal", "subtidal", "tidal", "wharf",
               "port ", "seabed", "ocean", "havre", "quai", "maritime", "estran"],
    "freshwater": ["river", "lake", "stream", "creek", "brook", "drain", "pond", "watercourse",
                   "rivière", "riviere", "lac ", "ruisseau", "étang", "etang", "cours d'eau",
                   "fleuve", "tributary", "wetland", "marsh"],
}

# first match wins, so the more specific patterns come first
TYPE_RULES = [
    (r"\bculvert|ponceau", "Road / culvert infrastructure"),
    (r"\bbridge\b|\bpont\b|passerelle", "Bridge / transportation infrastructure"),
    (r"dredg|dragage", "Dredging"),
    (r"pipeline|conduite|gazoduc|ol[ée]oduc", "Pipeline crossing"),
    (r"enrochement|bank stabiliz|stabilisation (?:de|des) berge|shoreline protection",
     "Bank stabilization"),
    (r"\bmine\b|mini[èe]re|mining|quarry|carri[èe]re", "Mine / mining"),
    (r"wharf|quai|harbour|harbor|marina|breakwater|brise-lame|boat launch|rampe de mise",
     "Port / marine infrastructure"),
    (r"railway|chemin de fer|\brail\b", "Railway infrastructure"),
    (r"highway|autoroute|\broad\b|\broute\b", "Highway infrastructure"),
    (r"subdivision|residential|r[ée]sidentiel|lotissement", "Residential development"),
    (r"water intake|prise d'eau|aqueduc", "Water intake infrastructure"),
    (r"barrage|\bdam\b|digue", "Dam / water control"),
    (r"[ée]missaire|outfall|sewer|[ée]gout|traitement des eaux", "Outfall / wastewater"),
]


def norm_num(v):
    return float(v) if isinstance(v, (int, float)) else None


def infer_setting(text):
    low = text.lower()
    score = {k: sum(low.count(w) for w in words) for k, words in SETTING_WORDS.items()}
    m, f = score["marine"], score["freshwater"]
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


def redactions(pages, start, end):
    found = set()
    for p in pages[start - 1:end]:
        for m in REDACTION_RX.finditer(p):
            found.add(re.sub(r"\s", "", m.group(0)))
    return "; ".join(sorted(found)) or None


def appears_in(value, text):
    """Whether a figure is written anywhere in the document, separators aside."""
    if value is None:
        return False
    whole = int(round(value))
    pats = [rf"\b{whole:,}\b".replace(",", r"[, ]?"), rf"\b{whole}\b"]
    return any(re.search(p, text) for p in pats)


def classify(sheet_val, cand, parts, block):
    """Say how a sheet figure relates to what the document states."""
    if sheet_val is None or cand is None:
        return None
    if abs(sheet_val - cand) <= max(1.0, sheet_val * 0.005):
        return None
    if abs(sheet_val - cand) <= max(1.0, sheet_val * 0.01):
        return ("reconcilable", "rounding")
    if parts and any(abs(sheet_val - p) <= 1 for p in parts):
        return ("reconcilable", "component-only: sheet holds one component of a summed figure")
    others = [float(x.replace(",", "").replace(" ", ""))
              for x in re.findall(r"\b\d[\d, ]{2,12}\b", block or "")]
    for o in others:
        if abs((cand - o) - sheet_val) <= max(1.0, sheet_val * 0.01):
            return ("reconcilable",
                    f"net vs gross: {cand:,.0f} less {o:,.0f} stated in the same clause")
    return ("contradiction", "figures differ")


def main(txt_path, segs_path):
    pages = load_pages(txt_path)
    segs = json.load(open(segs_path))
    wb = openpyxl.load_workbook(XLSX)
    ws = wb["Authorization_Summary"]

    hdr = [c.value for c in ws[1]]
    for name in NEW_COLS:
        if name not in hdr:
            hdr.append(name)
            ws.cell(row=1, column=len(hdr), value=name)
    idx = {h: i + 1 for i, h in enumerate(hdr)}

    def cell(r, c):
        return ws.cell(row=r, column=idx[c])

    by_file = {}
    for s in segs:
        by_file.setdefault(s["file_no"], []).append(s)
    for v in by_file.values():
        v.sort(key=lambda s: s["start"])

    # ---- row -> segment, using the anchor build_v2 already wrote ------------
    seg_at = {(s["start"], s["end"]): s for s in segs}
    row_seg = {}
    for r in range(2, ws.max_row + 1):
        key = (cell(r, "PDF_Page_Start").value, cell(r, "PDF_Page_End").value)
        if key in seg_at:
            row_seg[r] = seg_at[key]

    # ---- province spelling -------------------------------------------------
    fixed_prov = 0
    for r in range(2, ws.max_row + 1):
        v = cell(r, "Province").value
        if v and str(v).strip().lower() in PROVINCE_FIX:
            new = PROVINCE_FIX[str(v).strip().lower()]
            if new != str(v).strip():
                cell(r, "Province").value = new
                fixed_prov += 1

    # ---- amendments become their own rows ----------------------------------
    used = {}
    for r, s in row_seg.items():
        used.setdefault(s["file_no"], set()).add((s["start"], s["end"]))
    amendments = 0
    for file_no, group in by_file.items():
        if len(group) < 2 or file_no not in used:
            continue
        for s in group:
            if (s["start"], s["end"]) in used[file_no]:
                continue
            r = ws.max_row + 1
            ex = extract(pages, s)
            fr = front_fields(pages, s)
            anchor = f"PDF pp. {s['start']}-{s['end']}"
            if s.get("bates_start"):
                anchor += f" (Bates {s['bates_start']:06d}-{s['bates_end']:06d})"
            vals = {
                "Source_File": "A-2020-02093-MRV-FINAL.pdf", "DFO_File_or_PATH": file_no,
                "Proponent": fr["proponent"], "Project_Name_or_Description": fr["project"],
                "Province": fr["province"], "Contingency_Measures": ex["contingency"],
                "Monitoring_Requirements": ex["monitoring"], "Offsetting_Measures": ex["offsetting"],
                "Authorized_Impact_Summary": ex["impact_summary"],
                "PDF_Page_Start": s["start"], "PDF_Page_End": s["end"],
                "Bates_Start": s.get("bates_start"), "Bates_End": s.get("bates_end"),
                "Source_Page_Anchor": anchor, "Source_Reference_ID": anchor,
                "QA_Flag": "AUTO-ADDED - later document under the same file number, needs review",
                "Auto_Filled_Fields": "entire row",
                "Auto_Fill_Notes": f"Second or later document filed under {file_no}, at {anchor}.",
            }
            for k, v in vals.items():
                if k in idx and v not in (None, ""):
                    ws.cell(row=r, column=idx[k], value=v)
            row_seg[r] = s
            amendments += 1

    # ---- per-row annotation -------------------------------------------------
    disc = []
    counts = {"contradiction": 0, "reconcilable": 0, "unverified": 0}
    for r in range(2, ws.max_row + 1):
        s = row_seg.get(r)
        auto = str(cell(r, "QA_Flag").value or "").startswith("AUTO-ADDED")

        if s is None:
            cell(r, "Verification_Status").value = "not verified"
            cell(r, "Unverified_Reason").value = (
                "not-in-release: identifier does not appear anywhere in this PDF"
                if not cell(r, "PDF_Page_Start").value else
                "no-title-page: identifier appears only as a mention")
            counts["unverified"] += 1
            continue

        group = by_file.get(s["file_no"], [])
        first = group[0] if group else s
        cell(r, "Record_Type").value = (
            "amendment" if len(group) > 1 and (s["start"], s["end"]) != (first["start"], first["end"])
            else "authorization")

        red = redactions(pages, s["start"], s["end"])
        if red:
            cell(r, "Redaction_Exemptions").value = red

        text = seg_text(pages, s)
        if not cell(r, "Aquatic_Setting").value:
            cell(r, "Aquatic_Setting").value = infer_setting(text[:6000])
        if not cell(r, "Project_Type").value:
            cell(r, "Project_Type").value = infer_type(text[:6000])

        ex = extract(pages, s)
        notes, unver = [], []
        for col, key, xcol in (
                ("HADD_Destruction_m2", "destruction", "Extracted_HADD_Destruction_m2"),
                ("HADD_Alteration_m2", "alteration", "Extracted_HADD_Alteration_m2"),
                ("HADD_Disturbance_m2", "disruption", "Extracted_HADD_Disturbance_m2")):
            cand = ex["hadd_sum"].get(key)
            sheet_val = norm_num(cell(r, col).value)
            if cand is not None:
                cell(r, xcol).value = cand
            verdict = classify(sheet_val, cand, ex["hadd_parts"].get(key), ex["impact_summary"])
            if verdict:
                kind, reason = verdict
                counts[kind] += 1
                notes.append(kind)
                favours = ("workbook: this figure is written in the document, so the "
                           "extraction is probably mis-scoped"
                           if appears_in(sheet_val, text) else
                           "document: the workbook figure appears nowhere in this document")
                disc.append([r, cell(r, "DFO_File_or_PATH").value, col, sheet_val, cand,
                             ", ".join(f"{p:,.1f}" for p in (ex["hadd_parts"].get(key) or [])),
                             kind, reason, favours, cell(r, "Source_Page_Anchor").value,
                             (ex["impact_summary"] or "")[:600]])
            elif sheet_val is not None and cand is None:
                why = ("possibly-redacted: the document gives no figure here and carries "
                       f"exemption markers ({red})" if red else
                       "not-stated: the document gives no figure for this field")
                unver.append(f"{col}: {why}")
                counts["unverified"] += 1
                disc.append([r, cell(r, "DFO_File_or_PATH").value, col, sheet_val, None, "",
                             "unverified", why,
                             "workbook: figure is written in the document but was not extracted"
                             if appears_in(sheet_val, text) else "",
                             cell(r, "Source_Page_Anchor").value, ""])

        # a total nobody wrote down is arithmetic, not a quotation
        total = norm_num(cell(r, "HADD_Total_m2").value)
        if total is not None:
            stated = re.search(rf"{int(total):,}".replace(",", r"[, ]?") + r"\s*m", text)
            if not stated:
                cell(r, "Derived_Fields").value = "HADD_Total_m2 (arithmetic; not stated in document)"

        if auto:
            fno = str(cell(r, "DFO_File_or_PATH").value or "")
            n_sections = ex["n_sections"]
            if fno.startswith("Auth "):
                tier, basis = "tentative", "no legible PATH/SAPH number; identified by provincial authorisation number only"
            elif s.get("file_no_repaired"):
                tier, basis = "probable", "file number required OCR letter-for-digit repair"
            elif n_sections < 3:
                tier, basis = "probable", f"only {n_sections} numbered condition sections recognised"
            else:
                tier, basis = "confirmed", f"file number read from the page header; {n_sections} condition sections present"
            cell(r, "Confidence").value = tier
            cell(r, "Confidence_Basis").value = basis

        status = []
        if "contradiction" in notes:
            status.append(f"{notes.count('contradiction')} contradiction")
        if "reconcilable" in notes:
            status.append(f"{notes.count('reconcilable')} reconcilable")
        if unver:
            status.append(f"{len(unver)} unverified")
        cell(r, "Verification_Status").value = "; ".join(status) or "no discrepancies found"
        if unver:
            cell(r, "Unverified_Reason").value = " | ".join(unver)

    # ---- Discrepancies sheet ------------------------------------------------
    if "Discrepancies" in wb.sheetnames:
        del wb["Discrepancies"]
    d = wb.create_sheet("Discrepancies")
    d.append(["Row", "DFO_File_or_PATH", "Column", "Workbook_Value", "Document_Value",
              "Components_In_Document", "Type", "Reason", "Evidence_Favours",
              "Source_Page_Anchor", "Source_Sentence"])
    order = {"contradiction": 0, "unverified": 1, "reconcilable": 2}
    for row in sorted(disc, key=lambda x: (order.get(x[6], 3), x[0])):
        d.append(row)
    for c, w in zip("ABCDEFGHIJK", (6, 26, 26, 15, 15, 22, 14, 30, 56, 34, 80)):
        d.column_dimensions[c].width = w
    for c in d[1]:
        c.font = Font(bold=True)
    d.freeze_panes = "A2"

    for name in NEW_COLS:
        ws.column_dimensions[get_column_letter(idx[name])].width = 24
    for c in ws[1]:
        c.font = Font(bold=True)

    wb.save(XLSX)
    print(f"province spellings normalised : {fixed_prov}")
    print(f"amendment rows added          : {amendments}")
    print(f"rows now                      : {ws.max_row - 1}")
    print(f"discrepancy entries           : {len(disc)}")
    for k, v in counts.items():
        print(f"   {k:14s} {v}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
