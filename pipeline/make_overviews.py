"""Generate a compact overview page for each document folder, plus a root index."""
import html, os

ROOT = "/home/menser/Dropbox/BIZ/from_stantec"

CSS = """
:root{
  --paper:#F6F7F9; --card:#FFFFFF; --ink:#14181F; --ink-soft:#4A5462; --ink-faint:#6B7583;
  --rule:#DCE0E7; --rule-soft:#E9ECF1;
  --accent:#2C4A7C; --accent-soft:#EDF1F8; --accent-line:#B9C7DE;
  --bad:#A32C2C; --warn:#8A6212; --good:#2E6B4F;
  --f-display:"Spectral",Georgia,serif;
  --f-body:"Public Sans","Helvetica Neue",Arial,sans-serif;
  --f-mono:"IBM Plex Mono",Consolas,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --paper:#101318; --card:#171B22; --ink:#E7EAEF; --ink-soft:#A6AEBB; --ink-faint:#828C9B;
  --rule:#2A303A; --rule-soft:#222833;
  --accent:#8FAEDC; --accent-soft:#1A2231; --accent-line:#33445F;
  --bad:#E98A8A; --warn:#D9AE5E; --good:#7FBF9F;
}}
:root[data-theme="dark"]{
  --paper:#101318; --card:#171B22; --ink:#E7EAEF; --ink-soft:#A6AEBB; --ink-faint:#828C9B;
  --rule:#2A303A; --rule-soft:#222833;
  --accent:#8FAEDC; --accent-soft:#1A2231; --accent-line:#33445F;
  --bad:#E98A8A; --warn:#D9AE5E; --good:#7FBF9F;
}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--f-body);
  font-size:16.5px;line-height:1.6;-webkit-font-smoothing:antialiased}
.wrap{max-width:860px;margin:0 auto;padding:36px 26px 80px}
h1,h2{font-family:var(--f-display);text-wrap:balance;margin:0}
h1{font-size:clamp(1.8rem,4vw,2.5rem);line-height:1.08;letter-spacing:-.015em}
h2{font-size:1.22rem;font-weight:600;margin:0 0 8px;padding-bottom:8px;border-bottom:1px solid var(--rule)}
p{margin:0}
.eyebrow{font-family:var(--f-mono);font-size:11px;letter-spacing:.14em;text-transform:uppercase;
  color:var(--ink-faint);display:flex;flex-wrap:wrap;gap:5px 16px;margin-bottom:14px}
.back{font-family:var(--f-mono);font-size:11.5px;color:var(--accent);text-decoration:none;
  display:inline-block;margin-bottom:18px}
.back:hover{text-decoration:underline}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:1px;
  background:var(--rule);border:1px solid var(--rule);margin:22px 0 30px}
.stat{background:var(--card);padding:14px 16px;display:flex;flex-direction:column;gap:2px}
.stat .n{font-family:var(--f-mono);font-size:1.5rem;font-weight:600;font-variant-numeric:tabular-nums;line-height:1.1}
.stat .l{font-size:12px;color:var(--ink-soft);line-height:1.35}
.stat.good .n{color:var(--good)} .stat.bad .n{color:var(--bad)} .stat.warn .n{color:var(--warn)}
section{margin-bottom:32px}
section p+p{margin-top:11px}
.body-copy{color:var(--ink-soft)}
ul{margin:11px 0 0;padding-left:19px;display:flex;flex-direction:column;gap:7px}
li{line-height:1.55;color:var(--ink-soft)}
li::marker{color:var(--ink-faint)}
strong{font-weight:600;color:var(--ink)}
.scroll{overflow-x:auto;border:1px solid var(--rule);background:var(--card);margin-top:14px}
table{border-collapse:collapse;width:100%;font-size:13.5px}
th,td{text-align:left;padding:8px 12px;border-bottom:1px solid var(--rule-soft);vertical-align:top}
thead th{font-family:var(--f-mono);font-size:10px;letter-spacing:.1em;text-transform:uppercase;
  color:var(--ink-faint);font-weight:500;background:var(--rule-soft);white-space:nowrap}
tbody tr:last-child td{border-bottom:0}
td.f{font-family:var(--f-mono);font-size:12px;word-break:break-all}
.note{border-left:3px solid var(--warn);background:var(--card);padding:13px 17px;margin-top:16px}
.note p{font-size:14.5px;color:var(--ink-soft)}
a{color:var(--accent)}
footer{margin-top:44px;padding-top:18px;border-top:1px solid var(--rule);font-size:12.5px;color:var(--ink-faint)}
.idx{display:flex;flex-direction:column;gap:1px;background:var(--rule);border:1px solid var(--rule);margin-top:18px}
.idx a{background:var(--card);padding:15px 18px;text-decoration:none;display:block;color:inherit}
.idx a:hover{background:var(--accent-soft)}
.idx .t{font-weight:600;font-size:15px}
.idx .d{font-size:13.5px;color:var(--ink-soft);margin-top:3px}
.idx .m{font-family:var(--f-mono);font-size:11px;color:var(--ink-faint);margin-top:5px}
"""

HEAD = """<title>@@TITLE@@</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Spectral:wght@400;600;700&family=Public+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>%s</style>
""" % CSS


def page(title, eyebrow, h1, stats, blocks, back=True):
    out = [HEAD.replace("@@TITLE@@", html.escape(title)), '<div class="wrap">']
    if back:
        out.append('<a class="back" href="../index.html">&larr; all documents</a>')
    out.append('<div class="eyebrow">%s</div>' % "".join(f"<span>{html.escape(e)}</span>" for e in eyebrow))
    out.append(f"<h1>{html.escape(h1)}</h1>")
    if stats:
        out.append('<div class="stats">')
        for n, l, cls in stats:
            out.append(f'<div class="stat {cls}"><span class="n">{html.escape(str(n))}</span>'
                       f'<span class="l">{html.escape(l)}</span></div>')
        out.append("</div>")
    out.extend(blocks)
    out.append('<footer><p>Generated from the source PDF. Every figure on this page comes from '
               'the workbook or the document itself.</p></footer></div>')
    return "\n".join(out)


def sec(title, *body):
    return f"<section><h2>{html.escape(title)}</h2>" + "".join(body) + "</section>"


def para(t):
    return f'<p class="body-copy">{t}</p>'


def bullets(items):
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


def files_table(rows):
    h = "<thead><tr><th>File</th><th>What it is</th></tr></thead>"
    b = "".join(f'<tr><td class="f">{html.escape(a)}</td><td>{b}</td></tr>' for a, b in rows)
    return f'<div class="scroll"><table>{h}<tbody>{b}</tbody></table></div>'


def note(t):
    return f'<div class="note"><p>{t}</p></div>'


PAGES = {}

# ---------------------------------------------------------------- A-2019-01127
PAGES["A-2019-01127-NM-FINAL_pdf"] = page(
    "A-2019-01127 Package",
    ["Access to Information release A-2019-01127", "3,145 pages", "English"],
    "A-2019-01127-NM-FINAL",
    [("3,145", "pages", ""), ("18", "rows extracted", ""), ("12", "authorizations", ""),
     ("6", "amendments", ""), ("47", "quotes, all verified", "good"), ("6", "rows to confirm", "warn")],
    [
      sec("What this package is",
          para("Mostly <strong>not</strong> authorizations. The bulk of these 3,145 pages is fish habitat "
               "compensation plans, consultant reports and correspondence. The document on page 1 is a "
               "Golder compensation plan for the Red Chris project, dated January 2012."),
          para("Eighteen authorization records were found and extracted. That is a low count for a package "
               "this size, and it is the right count: the release is a correspondence file with "
               "authorizations scattered through it, not a stack of forms.")),
      sec("What is in this folder",
          files_table([
            ("A-2019-01127-NM-FINAL.pdf", "The release as delivered. Scanned, no text layer."),
            ("A-2019-01127-NM-FINAL_OCR.pdf", "Same pages with a searchable text layer added."),
            ("A-2019-01127-NM-FINAL_OCR.txt", "The text, one page per form feed. What the extraction reads."),
            ("A-2019-01127-NM-FINAL_authorizations.xlsx",
             "The extraction. Sheets: Authorization_Summary, Numeric_Review_Queue, Overview."),
          ])),
      sec("Particulars",
          bullets([
            "<strong>Older identifier format.</strong> This package uses <span class=\"f\">06-HPAC-PA1-00014</span> "
            "and <span class=\"f\">13-HPAC-PA7-00299</span>, which carry an extra regional segment the current "
            "format dropped. Anything matching only the modern pattern will miss these.",
            "<strong>Pacific-weighted.</strong> Fifteen rows are Pacific region, three Central and Arctic. "
            "Proponents include Terrane Metals, Teck Coal and Mount Polley Mining.",
            "<strong>Six rows are flagged tentative.</strong> Their proponent field reads as prose rather than "
            "a name, which means the structural test caught a letter about an authorization rather than the "
            "authorization form. Open those six page ranges before trusting the row.",
            "<strong>No province field.</strong> The older form does not carry one, so Province is empty on most "
            "rows and Region is derived from the file number instead.",
            "<strong>Eleven rows touch redacted pages</strong>, citing Access to Information exemptions.",
          ])),
      sec("Caveats",
          para("Only three habitat area figures were extracted. The older form states impacts as prose "
               "rather than as a bulleted list, so component summing has little to work with. Those three "
               "sit in Numeric_Review_Queue with their source sentence; the canonical HADD columns are empty."),
          note("There was no prior spreadsheet for this package, so nothing was reconciled and no accuracy "
               "figure can be quoted. Every row reads <span class=\"f\">unreconciled</span> for that reason.")),
    ])

# ---------------------------------------------------------------- A-2019-01128
PAGES["A-2019-01128-NM-FINAL_pdf"] = page(
    "A-2019-01128 Package",
    ["Access to Information release A-2019-01128", "2,512 pages", "English"],
    "A-2019-01128-NM-FINAL",
    [("2,512", "pages", ""), ("23", "rows extracted", ""), ("19", "authorizations", ""),
     ("4", "amendments", ""), ("56", "quotes, all verified", "good"), ("2", "rows to confirm", "warn")],
    [
      sec("What this package is",
          para("Another correspondence-heavy release. Page 1 is an email thread about Larose Creek, Yukon. "
               "Twenty-three authorization records were extracted from 2,512 pages, the rest being "
               "compensation plans, reports and email."),
          para("Twenty of the twenty-three are confirmed: the file number was read from the page header and "
               "the document carries three or more numbered condition sections.")),
      sec("What is in this folder",
          files_table([
            ("A-2019-01128-NM-FINAL.pdf", "The release as delivered. Scanned, no text layer."),
            ("A-2019-01128-NM-FINAL_OCR.pdf", "Same pages with a searchable text layer added."),
            ("A-2019-01128-NM-FINAL_OCR.txt", "The text, one page per form feed."),
            ("A-2019-01128-NM-FINAL_authorizations.xlsx",
             "The extraction. Sheets: Authorization_Summary, Numeric_Review_Queue, Overview."),
          ])),
      sec("Particulars",
          bullets([
            "<strong>Northern and Pacific.</strong> Fifteen rows Pacific, eight Central and Arctic. Proponents "
            "include Agnico Eagle Mines in Nunavut, Fortymile Gold Placers in Yukon and All-In Exploration "
            "Solutions.",
            "<strong>Two identifier generations appear.</strong> Eleven file numbers use the current "
            "format; sixteen use the older one with an extra regional segment, such as "
            "<span class=\"f\">10-HPAC-PA5-00050</span> and <span class=\"f\">03-HCAA-CA7-00191</span>. Some "
            "documents also carry a separate authorization number alongside the file number, of the form "
            "<span class=\"f\">NU-03-0191.4</span>.",
            "<strong>Placer mining figures are enormous.</strong> One authorization covers 2,994,330 m&sup2; of "
            "habitat, stated as 1,965,000 m&sup2; of river bar alteration plus 1,029,330 m&sup2; of removal. "
            "Figures at that scale are normal here and are not transcription errors.",
            "<strong>Seventeen rows touch redacted pages.</strong>",
            "<strong>Region and province agree on every row.</strong> No mismatches to investigate.",
          ])),
      sec("Caveats",
          para("As with the sibling package, only three habitat figures extracted cleanly, and there was no "
               "prior spreadsheet to reconcile against. Two rows are tentative because their proponent field "
               "did not parse as a name."),
          note("The scan is clean enough that OCR quality is not the limiting factor here. The limit is the "
               "older form's prose phrasing of impacts.")),
    ])

# ---------------------------------------------------------------- CBL
PAGES["A-2021-00215_CBL_pdf"] = page(
    "A-2021-00215 CBL Package",
    ["Access to Information release A-2021-00215", "46 pages", "English"],
    "A-2021-00215 CBL Release Package",
    [("46", "pages", ""), ("0", "authorizations", "bad"), ("0", "file numbers found", "bad")],
    [
      sec("What this package is",
          para("Not the same kind of document as the other releases, and there is nothing here for the "
               "authorization pipeline to extract."),
          para("The 46 pages are photographed meeting slides and a regulatory permitting timeline, heavily "
               "annotated by hand. Content covers Facility Alteration Permits, harbour master approvals and "
               "a construction schedule. No Fisheries Act authorization, no PATH or SAPH file number, none of "
               "the numbered condition sections the extraction keys on.")),
      sec("What is in this folder",
          files_table([
            ("A-2021-00215_CBL - Release Package.pdf", "The release as delivered. Scanned, no text layer."),
            ("A-2021-00215_CBL - Release Package_OCR.pdf", "Same pages with a searchable text layer added."),
            ("A-2021-00215_CBL - Release Package_OCR.txt", "The text. Rough, for the reason below."),
          ])),
      sec("Particulars",
          bullets([
            "<strong>No workbook was produced.</strong> Building one would mean inventing a schema for a "
            "document type with three examples of nothing in common.",
            "<strong>OCR quality is poor and that is inherent.</strong> These are photographs of projected "
            "slides overlaid with handwriting. Typed text came through; the handwriting did not.",
            "<strong>Still worth having searchable.</strong> The text layer makes the package greppable for "
            "names, dates and permit types even where the OCR is imperfect.",
          ])),
      sec("Caveats",
          note("Treat the extracted text as a search aid, not as a transcript. Read anything that matters "
               "on the page.")),
    ])

# ---------------------------------------------------------------- AOR letter
PAGES["AOR-2026-00383_pdf"] = page(
    "AOR-2026-00383 Response Letter",
    ["Informal request response", "1 page", "Born-digital"],
    "AOR-2026-00383 Response Letter",
    [("1", "page", ""), ("0", "OCR needed", "good")],
    [
      sec("What this is",
          para("A single-page response letter from Fisheries and Oceans Canada, dated 10 July 2026. It "
               "answers four informal requests, each a re-release of an earlier Access to Information "
               "request, and it is the document that ties this set together rather than a record to extract."),
          para("The letter names all four: AOR-2026-00380 re-releases A-2020-02093, AOR-2026-00381 "
               "re-releases A-2019-01128, AOR-2026-00382 re-releases A-2019-01127, and AOR-2026-00383 "
               "re-releases A-2021-00215. The placer guidebook is not among them."),
          para("The PDF was produced by Word and already carries a real text layer, so no OCR was run.")),
      sec("What is in this folder",
          files_table([
            ("AOR-2026-00383 - Response Informal Many Requests - Signed.pdf", "The letter as delivered."),
            ("AOR-2026-00383 - Response Informal Many Requests - Signed.txt",
             "Plain text extracted from the PDF's own text layer."),
          ])),
      sec("Particulars",
          bullets([
            "<strong>Marked PROTECTED A.</strong> Handle accordingly.",
            "<strong>No workbook.</strong> One page of correspondence has nothing to tabulate.",
            "<strong>It is the provenance record for the set.</strong> If anyone asks where these four "
            "packages came from or which request each answers, the answer is on this page.",
          ])),
    ])

# ---------------------------------------------------------------- guidebook
PAGES["emr-placer-guidebook-mitigation-measures_pdf"] = page(
    "Yukon Placer Guidebook Index",
    ["Yukon placer mining guidance", "132 pages", "Born-digital"],
    "Guidebook of Mitigation Measures for Placer Mining in the Yukon",
    [("132", "pages", ""), ("88", "sections indexed", ""), ("475", "guidance statements", ""),
     ("86", "must or shall", "bad"), ("281", "should", "warn"), ("475", "quotes verified", "good")],
    [
      sec("What this is",
          para("A technical guidebook dated 1 November 2010, not a release package. It sets out how to build "
               "a fish habitat compensation and restoration plan for placer mining: watershed and stream "
               "classification, channel design, flood requirements, and mitigation measures by mining method "
               "and project phase."),
          para("Because the document type is different, the schema is different. There are no authorizations "
               "to tabulate, so the workbook indexes the document's own structure instead. The conventions are "
               "unchanged: every row cites a page, and every quoted sentence is verbatim.")),
      sec("What is in this folder",
          files_table([
            ("emr-placer-guidebook-mitigation-measures.pdf", "The guidebook. Born-digital, already searchable."),
            ("emr-placer-guidebook-mitigation-measures_text.txt", "Text extracted from the PDF, one page per form feed."),
            ("emr-placer-guidebook-guidance-register.xlsx",
             "Sections, Guidance_Register, Overview and Methodology."),
          ])),
      sec("How to use the workbook",
          bullets([
            "<strong>Sections</strong> indexes all 88 numbered headings with a contiguous page range each, so "
            "any part of the guidebook can be cited by section number and page.",
            "<strong>Guidance_Register</strong> holds one row per sentence carrying an obligation word, with "
            "the section it sits in and the page it is on.",
            "<strong>Modality is recorded, not normalised.</strong> 86 statements say must or shall, 108 say "
            "required or recommended, 281 say should. Collapsing those into one bucket would lose the "
            "distinction between a requirement and advice, which in a guidance document is the whole point.",
          ])),
      sec("Caveats",
          para("Figures, worked equations and tabular data are not captured. The guidebook carries channel "
               "design formulas whose meaning depends on layout that flat text does not preserve, so those "
               "must be read on the page."),
          note("No OCR was involved, so there is no OCR error to allow for. Every one of the 475 quoted "
               "statements was confirmed present on the page it cites.")),
    ])

# ---------------------------------------------------------------- root index
INDEX_ROWS = [
    ("A-2020-02093-MRV-FINAL_pdf/reconciliation.html", "A-2020-02093-MRV-FINAL",
     "Dense stack of Fisheries Act authorizations, reconciled against an existing working spreadsheet.",
     "1,842 pages &middot; 133 rows &middot; 332 verified quotes &middot; full report"),
    ("A-2019-01127-NM-FINAL_pdf/overview.html", "A-2019-01127-NM-FINAL",
     "Compensation plans and correspondence with authorizations scattered through them.",
     "3,145 pages &middot; 18 rows &middot; 47 verified quotes"),
    ("A-2019-01128-NM-FINAL_pdf/overview.html", "A-2019-01128-NM-FINAL",
     "Correspondence file, northern and Pacific placer and mining authorizations.",
     "2,512 pages &middot; 23 rows &middot; 56 verified quotes"),
    ("emr-placer-guidebook-mitigation-measures_pdf/overview.html",
     "Guidebook of Mitigation Measures for Placer Mining in the Yukon",
     "Technical guidance, indexed by section with its obligations registered.",
     "132 pages &middot; 88 sections &middot; 475 guidance statements"),
    ("A-2021-00215_CBL_pdf/overview.html", "A-2021-00215 CBL Release Package",
     "Photographed meeting slides and a permitting timeline. No authorizations.",
     "46 pages &middot; no workbook"),
    ("AOR-2026-00383_pdf/overview.html", "AOR-2026-00383 Response Letter",
     "The covering letter for this set of releases.",
     "1 page &middot; no workbook"),
]

idx_body = ['<div class="idx">']
for href, title, desc, meta in INDEX_ROWS:
    idx_body.append(f'<a href="{href}"><div class="t">{html.escape(title)}</div>'
                    f'<div class="d">{html.escape(desc)}</div><div class="m">{meta}</div></a>')
idx_body.append("</div>")

PAGES["__index__"] = page(
    "Stantec Release Set",
    ["Fisheries and Oceans Canada", "four release packages", "7,678 pages"],
    "Stantec Release Set",
    [("6", "documents on file", ""), ("7,678", "pages", ""), ("174", "authorization rows", ""),
     ("910", "quotes verified", "good")],
    [
      sec("What this is",
          para("Five documents came as one Access to Information delivery: four release packages and the "
               "covering letter that lists them. The Yukon placer mining guidebook is filed here too, but it "
               "arrived separately and is not part of that release."),
          para("Each has its own folder holding the original PDF, a searchable version where OCR was needed, "
               "the extracted text, and a workbook where there was something to tabulate."),
          para("Open any overview below for what that document is and what came out of it.")),
      sec("The documents", "".join(idx_body)),
      sec("How to read any extraction",
          bullets([
            "<strong>Every row cites its pages.</strong> Source_Page_Anchor gives the PDF page range and the "
            "Bates range. Open the page and check the row against it.",
            "<strong>Page numbers are not Bates numbers.</strong> They run together at the front of a package "
            "and drift apart later, which is why both are recorded.",
            "<strong>A value ending in (i) was inferred</strong>, not quoted. Good enough to sort and filter, "
            "not to cite.",
            "<strong>Habitat area figures are never auto-filled.</strong> Candidates sit in a review queue with "
            "the sentence they came from, because automatic extraction is not accurate enough to write "
            "regulatory figures unattended.",
          ])),
    ], back=False)


for folder, doc in PAGES.items():
    path = os.path.join(ROOT, "index.html" if folder == "__index__" else f"{folder}/overview.html")
    open(path, "w", encoding="utf-8").write(doc)
    print("wrote", path.replace(ROOT + "/", ""))
