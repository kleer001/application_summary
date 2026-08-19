"""Index a technical guidebook: numbered sections and the guidance they carry.

A guidebook is not an authorization stack, so the schema differs. The conventions
do not: every row cites the page it came from, and every text value is verbatim.

Usage: build_guidebook.py <text.txt> <out.xlsx> <source-pdf-name>
"""
import re, sys
import openpyxl
from openpyxl.styles import Font, Alignment

HEADING_RX = re.compile(r"^[ \t]{0,8}(\d+(?:\.\d+)*)[ \t]+([A-Z][^\n]{3,90}?)[ \t]*$", re.M)
# a table-of-contents line ends in dot leaders and a page number
TOC_RX = re.compile(r"\.{3,}\s*\d+\s*$|\s\d+\s*$")

MODALITY = [
    ("must", re.compile(r"\bmust\b", re.I)),
    ("shall", re.compile(r"\bshall\b", re.I)),
    ("required", re.compile(r"\brequired\b|\brequirement\b", re.I)),
    ("recommended", re.compile(r"\brecommended\b", re.I)),
    ("should", re.compile(r"\bshould\b", re.I)),
]
# Sentences wrap across lines in the layout text, so bodies are flattened
# per page before splitting and offsets are mapped back to a page number.
SENT_RX = re.compile(r"[^.]{25,400}?\.(?=\s|$)")


def clean(s):
    return re.sub(r"\s+", " ", s).strip()


def find_sections(pages):
    """Numbered headings, skipping the table of contents at the front."""
    seen, out = set(), []
    for i, pg in enumerate(pages, 1):
        for m in HEADING_RX.finditer(pg):
            num, title = m.group(1), m.group(2).strip()
            if TOC_RX.search(title):
                continue                      # contents entry, not the section itself
            if num in seen:
                continue
            seen.add(num)
            out.append({"number": num, "title": clean(title), "page": i,
                        "level": num.count(".") + 1})
    out.sort(key=lambda s: s["page"])
    for i, s in enumerate(out):
        s["end"] = out[i + 1]["page"] - 1 if i + 1 < len(out) else len(pages)
        if s["end"] < s["page"]:
            s["end"] = s["page"]
    return out


def section_at(sections, page):
    best = None
    for s in sections:
        if s["page"] <= page:
            best = s
        else:
            break
    return best


def main(txt_path, out_path, source_name):
    pages = open(txt_path, encoding="utf-8", errors="replace").read().split("\f")
    if pages and not pages[-1].strip():
        pages.pop()            # trailing form feed is not a page
    sections = find_sections(pages)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sections"
    ws.append(["Section_Number", "Level", "Title", "PDF_Page_Start", "PDF_Page_End",
               "Source_Page_Anchor", "Guidance_Items", "Source_File"])
    register = []

    for s in sections:
        flat, marks, cursor = [], [], 0
        for offset, pg in enumerate(pages[s["page"] - 1:s["end"]]):
            t = clean(pg)
            flat.append(t)
            marks.append((cursor, s["page"] + offset))
            cursor += len(t) + 1
        body = " ".join(flat)

        def page_of(pos):
            hit = marks[0][1]
            for start, page in marks:
                if start <= pos:
                    hit = page
                else:
                    break
            return hit

        items = 0
        for m in SENT_RX.finditer(body):
            sent = clean(m.group(0))
            # a heading can run into the first sentence under it; drop the shout
            sent = re.sub(r"^[\d.\s]*(?:[A-Z][A-Z\s/&'\-]{6,}\s)+", "", sent).strip()
            if len(sent.split()) < 8:
                continue
            mod = next((name for name, rx in MODALITY if rx.search(sent)), None)
            if not mod:
                continue
            page = page_of(m.start())
            register.append([s["number"], s["title"], mod, sent, page,
                             f"PDF p. {page}", source_name])
            items += 1
        ws.append([s["number"], s["level"], s["title"], s["page"], s["end"],
                   f"PDF pp. {s['page']}-{s['end']}", items, source_name])

    g = wb.create_sheet("Guidance_Register")
    g.append(["Section_Number", "Section_Title", "Modality", "Guidance_Text",
              "PDF_Page", "Source_Page_Anchor", "Source_File"])
    for r in register:
        g.append(r)

    counts = {}
    for r in register:
        counts[r[2]] = counts.get(r[2], 0) + 1

    ov = wb.create_sheet("Overview")
    ov.append(["Metric", "Value"])
    for k, v in [
        ("Source PDF", source_name),
        ("Pages", len(pages)),
        ("Numbered sections indexed", len(sections)),
        ("Guidance statements captured", len(register)),
        ("  must / shall", counts.get("must", 0) + counts.get("shall", 0)),
        ("  required / recommended", counts.get("required", 0) + counts.get("recommended", 0)),
        ("  should", counts.get("should", 0)),
        ("Text source", "Born-digital PDF text layer; no OCR was needed or used."),
        ("Note", "Guidance_Text is verbatim. Modality records which obligation word the "
                 "sentence uses, which is what separates a requirement from advice. "
                 "Sentences are captured whole, so a page reference points at the sentence, "
                 "not at a summary of it."),
    ]:
        ov.append([k, v])

    me = wb.create_sheet("Methodology")
    me.append(["Topic", "Detail"])
    for k, v in [
        ("Document type", "A technical guidebook, not a stack of authorizations. The section "
                          "index and guidance register replace the authorization schema; the "
                          "page-anchor convention is the same."),
        ("Sections", "Numbered headings read from the page text. Table-of-contents lines are "
                     "skipped by their dot leaders and trailing page number, so each section "
                     "is indexed once, at the page where it actually begins."),
        ("Section ranges", "A section runs from its heading to the page before the next "
                           "heading, so ranges are contiguous and every page belongs to one."),
        ("Guidance capture", "Whole sentences containing an obligation word. Modality is "
                             "recorded rather than normalised, because must and should carry "
                             "different weight and collapsing them would lose that."),
        ("Not captured", "Figures, worked equations and tabular data. The guidebook carries "
                         "design formulas whose meaning depends on layout that flat text "
                         "does not preserve; read those on the page."),
    ]:
        me.append([k, v])

    for sheet, widths in ((ws, (16, 7, 60, 15, 15, 24, 15, 40)),
                          (g, (16, 40, 13, 96, 10, 18, 34)),
                          (ov, (36, 92)), (me, (22, 100))):
        for c in sheet[1]:
            c.font = Font(bold=True)
        sheet.freeze_panes = "A2"
        for col, w in zip("ABCDEFGH", widths):
            sheet.column_dimensions[col].width = w
    for sheet in (ov, me):
        for r in range(2, sheet.max_row + 1):
            sheet.cell(row=r, column=2).alignment = Alignment(wrap_text=True, vertical="top")

    wb.save(out_path)
    print(f"{source_name}: {len(sections)} sections, {len(register)} guidance statements "
          f"(must/shall {counts.get('must',0)+counts.get('shall',0)}, "
          f"should {counts.get('should',0)}) -> {out_path}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
