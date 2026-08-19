"""Fill the v2 workbook from the OCR text: page anchors, quoted condition text,
split offsetting units, resolved identifiers, and a numeric review queue.

Existing cell values are never overwritten.
"""
import json, re, sys
import openpyxl
from openpyxl.styles import Font, Alignment
from openpyxl.utils import get_column_letter

from segment import load_pages, FILE_RX, norm_file
from extract import extract, front_fields, measures, num

XLSX = "/home/menser/Dropbox/BIZ/from_stantec/A-2020-02093-MRV-FINAL_pdf/DFO_2021_FAA_offsetting_summary_WORKING_v2.xlsx"

NEW_COLS = [
    "PDF_Page_Start", "PDF_Page_End", "Bates_Start", "Bates_End", "Source_Page_Anchor",
    "Offsetting_Required_Value", "Offsetting_Required_Unit",
    "Offsetting_Provided_Value", "Offsetting_Provided_Unit",
    "Resolved_DFO_File", "Legacy_Reference_ID", "Auto_Filled_Fields", "Auto_Fill_Notes",
]

FILL_TEXT = [                       # workbook column  <- extractor key
    ("Contingency_Measures", "contingency"),
    ("Monitoring_Requirements", "monitoring"),
    ("Offsetting_Measures", "offsetting"),
    ("Authorized_Impact_Summary", "impact_summary"),
]

UNIT_RX = re.compile(
    r"([\d][\d,\. ]{0,14}?)\s*(m\s*[2²?7*°~^o]|hectares?|ha\b|linear\s+met(?:re|er)s|units?)", re.I)
RATIO_RX = re.compile(r"([\d\.]+)\s*(?::|to)\s*1", re.I)


def parse_amount(val):
    """('5,688 m2.') -> (5688.0, 'm2'); returns (None, None) when not a plain amount."""
    if val in (None, ""):
        return None, None
    s = str(val)
    m = UNIT_RX.search(s)
    if not m:
        r = RATIO_RX.search(s)
        return (None, f"ratio {r.group(1)}:1") if r else (None, None)
    v = num(m.group(1))
    unit = m.group(2).lower()
    unit = "m2" if unit.startswith("m") and "lin" not in unit else \
           "ha" if unit.startswith("h") else \
           "linear m" if "lin" in unit else "units"
    return v, (unit if v else None)


def anchor(sg):
    a = f"PDF pp. {sg['start']}-{sg['end']}"
    if sg.get("bates_start"):
        a += f" (Bates {sg['bates_start']:06d}-{sg['bates_end']:06d})"
    pe = sg.get("package_end")
    if pe and pe > sg["end"]:
        a += f"; attachments to p. {pe}"
    return a



def page_hits(pages, ids):
    """Pages where any of these identifiers appear, for rows with no title page."""
    out = []
    for i, p in enumerate(pages, 1):
        if any(x in p for x in ids):
            out.append(i)
    return out


def resolve_by_name(pages, segs, matched, proponent, project):
    """Match a row with an unusable identifier to a leftover segment by proponent name.

    Scored on how much of the *document's* proponent appears in the row, since a row
    often carries a longer combined name ("Peter Hyde / Countryside Developments Inc.").
    """
    if not proponent:
        return None
    row_toks = set(re.sub(r"[^a-z0-9 ]", " ", f"{proponent} {project or ''}".lower()).split())
    best, best_score = None, 0.0
    for s in segs:
        if s["file_no"] in matched:
            continue
        fr = front_fields(pages, s)
        cand = re.sub(r"[^a-z0-9 ]", " ", str(fr.get("proponent") or "").lower())
        toks = {t for t in cand.split() if len(t) > 3} - {"ltd", "inc", "limited", "corporation", "company"}
        if len(toks) < 2:
            continue
        score = len(toks & row_toks) / len(toks)
        if score > best_score:
            best, best_score = s, score
    return best if best_score >= 0.85 else None



def assign_parts(ws, idx):
    """Infer Source_Part for rows that lack one, from where the known parts start.

    The release was split into sequentially numbered parts, so a part runs from the
    first page any of its rows cite to the page before the next part's first page.
    """
    firsts = {}
    for r in range(2, ws.max_row + 1):
        part = ws.cell(row=r, column=idx["Source_Part"]).value
        start = ws.cell(row=r, column=idx["PDF_Page_Start"]).value
        if not part or not isinstance(start, int):
            continue
        m = re.search(r"\d+", str(part))
        if m:
            n = int(m.group())
            firsts[n] = min(firsts.get(n, start), start)
    if not firsts:
        return 0
    order = sorted(firsts)
    bounds = []
    for i, n in enumerate(order):
        end = firsts[order[i + 1]] - 1 if i + 1 < len(order) else None
        bounds.append((n, firsts[n], end))
    filled = 0
    for r in range(2, ws.max_row + 1):
        if ws.cell(row=r, column=idx["Source_Part"]).value:
            continue
        start = ws.cell(row=r, column=idx["PDF_Page_Start"]).value
        if not isinstance(start, int):
            continue
        for n, lo, hi in bounds:
            # a page past the last known part start cannot be placed
            if start >= lo and (hi is None or start <= hi) and hi is not None:
                ws.cell(row=r, column=idx["Source_Part"]).value = f"Part {n} (i)"
                filled += 1
                break
    return filled


def main(txt_path, segs_path):
    pages = load_pages(txt_path)
    segs = json.load(open(segs_path, encoding="utf-8"))
    wb = openpyxl.load_workbook(XLSX)
    ws = wb["Authorization_Summary"]

    hdr = [c.value for c in ws[1]]
    for name in NEW_COLS:
        if name not in hdr:
            hdr.append(name)
            ws.cell(row=1, column=len(hdr), value=name)
    idx = {h: i + 1 for i, h in enumerate(hdr)}

    by_file, by_auth = {}, {}
    for s in segs:
        by_file.setdefault(s["file_no"], []).append(s)
        an = s.get("auth_no") or front_fields(pages, s).get("auth_number")
        if an:
            by_auth.setdefault(re.sub(r"\s", "", an), []).append(s)
    for v in list(by_file.values()) + list(by_auth.values()):
        v.sort(key=lambda s: s["start"])

    stats = {"rows_mapped": 0, "cells_filled": 0, "unmapped": [], "review": [], "resolved": []}
    ci = idx["DFO_File_or_PATH"]
    matched_files = set()
    for r in range(2, ws.max_row + 1):
        whole = " ".join(str(c.value) for c in ws[r] if c.value is not None)
        for m in FILE_RX.findall(whole):
            matched_files.add(norm_file(m))

    for r in range(2, ws.max_row + 1):
        raw_id = str(ws.cell(row=r, column=ci).value or "")
        ids = [norm_file(m) for m in FILE_RX.findall(raw_id)]
        sg = next((by_file[i][0] for i in ids if i in by_file), None)
        if sg is None:
            # Quebec rows are keyed by the provincial authorisation number
            auths = [re.sub(r"\s", "", a) for a in
                     re.findall(r"(?:Auth(?:orization)?\.?\s*)(\d{4}\s*-\s*\d{2,3})", raw_id, re.I)]
            sg = next((by_auth[a][0] for a in auths if a in by_auth), None)
            if sg is not None:
                ws.cell(row=r, column=idx["Resolved_DFO_File"]).value = sg["file_no"]
                stats["resolved"].append((r, raw_id, sg["file_no"], anchor(sg)))
        if sg is None:
            sg = resolve_by_name(pages, segs, matched_files,
                                 ws.cell(row=r, column=idx["Proponent"]).value,
                                 ws.cell(row=r, column=idx["Project_Name_or_Description"]).value)
            if sg is None:
                hits = [i for i in ids if i] and page_hits(pages, ids)
                if hits:
                    ws.cell(row=r, column=idx["PDF_Page_Start"]).value = hits[0]
                    ws.cell(row=r, column=idx["PDF_Page_End"]).value = hits[-1]
                    note = (f"PDF pp. {hits[0]}-{hits[-1]} (identifier mentions only; "
                            f"no authorization title page detected)")
                    ws.cell(row=r, column=idx["Source_Page_Anchor"]).value = note
                    ws.cell(row=r, column=idx["Auto_Fill_Notes"]).value = note
                stats["unmapped"].append((r, raw_id, hits[:6] if hits else []))
                continue
            matched_files.add(sg["file_no"])
            ws.cell(row=r, column=idx["Resolved_DFO_File"]).value = sg["file_no"]
            stats["resolved"].append((r, raw_id, sg["file_no"], anchor(sg)))
        matched_files.add(sg["file_no"])
        stats["rows_mapped"] += 1
        ex = extract(pages, sg)
        filled = []

        def put(col, value):
            if value in (None, ""):
                return
            cell = ws.cell(row=r, column=idx[col])
            if cell.value in (None, ""):
                cell.value = value
                filled.append(col)
                stats["cells_filled"] += 1

        put("PDF_Page_Start", sg["start"]); put("PDF_Page_End", sg["end"])
        put("Bates_Start", sg.get("bates_start")); put("Bates_End", sg.get("bates_end"))
        put("Source_Page_Anchor", anchor(sg))

        for col, key in FILL_TEXT:
            put(col, ex.get(key))

        # preserve the unusable citation token, then replace it with a real anchor
        legacy = ws.cell(row=r, column=idx["Source_Reference_ID"]).value
        if legacy and str(legacy).startswith("turn"):
            ws.cell(row=r, column=idx["Legacy_Reference_ID"]).value = legacy
            ws.cell(row=r, column=idx["Source_Reference_ID"]).value = anchor(sg)

        for src_col, val_col, unit_col in (
                ("Offsetting_Required", "Offsetting_Required_Value", "Offsetting_Required_Unit"),
                ("Offsetting_Provided", "Offsetting_Provided_Value", "Offsetting_Provided_Unit")):
            v, u = parse_amount(ws.cell(row=r, column=idx[src_col]).value)
            put(val_col, v); put(unit_col, u)

        # numeric HADD figures are queued for human confirmation, never written
        for col, key in (("HADD_Destruction_m2", "destruction"),
                         ("HADD_Alteration_m2", "alteration"),
                         ("HADD_Disturbance_m2", "disruption")):
            cur = ws.cell(row=r, column=idx[col]).value
            cand = ex["hadd_sum"].get(key)
            if cand is None:
                continue
            cur_n = float(cur) if isinstance(cur, (int, float)) else None
            if cur_n is not None and abs(cur_n - cand) <= max(1.0, cur_n * 0.005):
                continue
            stats["review"].append({
                "row": r, "file": raw_id, "column": col,
                "current": cur, "candidate": cand,
                "components": ex["hadd_parts"].get(key),
                "anchor": anchor(sg),
                "evidence": (ex["impact_summary"] or "")[:600],
            })

        if filled:
            ws.cell(row=r, column=idx["Auto_Filled_Fields"]).value = ", ".join(filled)
            ws.cell(row=r, column=idx["Auto_Fill_Notes"]).value = f"Quoted from {anchor(sg)}"

    # authorizations present in the PDF with no row at all
    added = []
    for s in segs:
        if s["file_no"] in matched_files:
            continue
        ex = extract(pages, s); fr = front_fields(pages, s)
        row = ws.max_row + 1
        vals = {
            "Source_Part": "", "Source_File": "A-2020-02093-MRV-FINAL.pdf",
            "DFO_File_or_PATH": s["file_no"],
            "Proponent": fr["proponent"],
            "Project_Name_or_Description": fr["project"], "Province": fr["province"],
            "Contingency_Measures": ex["contingency"], "Monitoring_Requirements": ex["monitoring"],
            "Offsetting_Measures": ex["offsetting"], "Authorized_Impact_Summary": ex["impact_summary"],
            "PDF_Page_Start": s["start"], "PDF_Page_End": s["end"],
            "Bates_Start": s.get("bates_start"), "Bates_End": s.get("bates_end"),
            "Source_Page_Anchor": anchor(s), "Source_Reference_ID": anchor(s),
            "QA_Flag": "AUTO-ADDED - absent from prior workbook, needs review",
            "Auto_Filled_Fields": "entire row",
            "Auto_Fill_Notes": (f"Authorization found in PDF at {anchor(s)} with no matching row. "
                                "Authorization date left blank: the issue date is a stamp that OCR does not "
                                "reliably capture, and nearby dates are condition periods."),
        }
        for k, v in vals.items():
            if k in idx and v not in (None, ""):
                ws.cell(row=row, column=idx[k], value=v)
        added.append((s["file_no"], anchor(s), fr["proponent"]))

    parts_filled = assign_parts(ws, idx)

    # review-queue sheet
    if "Numeric_Review_Queue" in wb.sheetnames:
        del wb["Numeric_Review_Queue"]
    q = wb.create_sheet("Numeric_Review_Queue")
    qh = ["Row", "DFO_File_or_PATH", "Column", "Current_Value", "Extracted_Candidate",
          "Components_Found", "Source_Page_Anchor", "Source_Sentence"]
    q.append(qh)
    for it in stats["review"]:
        q.append([it["row"], it["file"], it["column"], it["current"], it["candidate"],
                  ", ".join(str(x) for x in (it["components"] or [])), it["anchor"], it["evidence"]])
    for c, w in zip("ABCDEFGH", (6, 26, 24, 14, 18, 24, 34, 90)):
        q.column_dimensions[c].width = w
    for c in q[1]:
        c.font = Font(bold=True)
    q.freeze_panes = "A2"

    for c in ws[1]:
        c.font = Font(bold=True)
    ws.freeze_panes = "A2"
    for name in NEW_COLS:
        ws.column_dimensions[get_column_letter(idx[name])].width = 22

    wb.save(XLSX)
    json.dump(stats, open("build_stats.json", "w", encoding="utf-8"),
              indent=1, default=str, ensure_ascii=False)
    print(f"rows mapped      : {stats['rows_mapped']}")
    print(f"cells filled     : {stats['cells_filled']}")
    print(f"rows appended    : {len(added)}")
    for a in added:
        print(f"   + {a[0]}  {a[1]}  {a[2]}")
    print(f"identifiers resolved by name: {len(stats['resolved'])}")
    for rr in stats["resolved"]:
        print(f"   ~ row{rr[0]}: {rr[1]!r} -> {rr[2]}  {rr[3]}")
    print(f"unmapped rows    : {len(stats['unmapped'])}")
    for u in stats["unmapped"]:
        print(f"   ? row{u[0]}: {u[1]}  mentions_on_pages={u[2] if len(u) > 2 else []}")
    print(f"Source_Part inferred for {parts_filled} rows")
    print(f"numeric review queue entries: {len(stats['review'])}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
