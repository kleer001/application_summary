# application_summary

Turns a scanned government release package into a spreadsheet where every filled
cell cites the page it came from.

Built against Fisheries and Oceans Canada Access to Information releases —
stacks of Fisheries Act paragraph 35(2)(b) authorizations, thousands of pages
per package, no text layer. The approach carries to any release built from a
repeating official form.

## What is in this repo

`pipeline/` holds the scripts. The `*_pdf/` folders hold one worked example per
document: the OCR text, the workbook built from it, and an HTML overview.

The source PDFs and the searchable copies OCR produced are **not** here — together
they run to several gigabytes. Three small ones are kept because they are useful to
have alongside their extraction: the placer guidebook, the CBL release package and
the covering letter. The three large release PDFs and their OCR'd copies stay with
the delivery.

The file tables on each overview page describe the full working folder, so they list
PDFs that are not in this copy. Open `index.html` for the set.

## What it produces

One row per authorization, with:

- the numbered condition sections quoted verbatim (contingency, monitoring,
  offsetting) and the impact clause
- front-matter fields: proponent, project description, province, waterbody
- a page anchor: the PDF page range, the Bates range, and any attachment span
- a confidence tier and the evidence for it
- Access to Information exemptions cited anywhere in the document's pages

Two entry points:

| Script | Use when |
|---|---|
| `build_v2.py` + `annotate.py` | A spreadsheet already exists and needs reconciling against the source. Fills only empty cells, never overwrites, and records every disagreement. |
| `build_new.py` | No spreadsheet exists. Builds one from the PDF with the same column set, so workbooks from different releases concatenate. |

Windows users: see `WINDOWS.md`, which covers a locked-down machine with no
administrator rights. Ghostscript is not required there.

## Running it

Requires `ocrmypdf`, `tesseract` (with the language data you need) and
`openpyxl`. Ghostscript comes with ocrmypdf's dependencies.

```sh
# 1. Give the scan a text layer. Include every language in the package.
ocrmypdf --language eng+fra --output-type pdf --skip-text --rotate-pages \
         --optimize 0 --jobs "$(nproc)" \
         --sidecar RELEASE_OCR.txt RELEASE.pdf RELEASE_OCR.pdf

# 2. Find where each document starts and ends.
python pipeline/segment.py RELEASE_OCR.txt segs.json

# 3a. No prior spreadsheet:
python pipeline/build_new.py RELEASE_OCR.txt segs.json out.xlsx RELEASE.pdf

# 3b. Reconciling an existing one (edit the XLSX path at the top of each script):
python pipeline/build_v2.py RELEASE_OCR.txt segs.json
python pipeline/annotate.py RELEASE_OCR.txt segs.json
python pipeline/polish.py
```

The OCR step dominates. Two measured runs on 32 cores against 400 dpi scans:
7,545 pages in 66 minutes, and 1,842 pages in 13 minutes — 114 and 142 pages
per minute. Everything after OCR runs in seconds: segment, build, annotate and
polish together took 2.8 seconds over a 1,842-page package.

## How documents are found

Not by title. OCR breaks title lines — real examples from these releases include
`AUTORISA TION` and `AL INÉAS` — and the same form has at least six wordings
across languages and years.

A document starts where an "issued to" block appears near the top of a page,
backed by a file-number header, an authorisation-number header, or a
location/project-description section. Cover letters carry none of those and are
skipped. A document ends at whichever comes last: the final page carrying its own
file-number stamp, or its closing/signature block. Anything after that up to the
next document is recorded as attachments.

## What is deliberately not automated

**Habitat area figures.** Impact clauses list components that must be summed, cap
figures with "up to", and sometimes state a net figure after subtracting habitat
created. Measured against known-good values, extraction agreed 76% of the time on
destruction, 93% on alteration and 75% on disturbance. Candidates go to a
`Numeric_Review_Queue` sheet with the components found and the source sentence.
The canonical columns stay empty until a person confirms them.

**Authorization dates.** The issue date is a rubber stamp that OCR frequently
cannot read, and the dates nearest the top of a document are usually condition
periods. Guessing produces confident, wrong dates.

**Classification.** Aquatic setting and project type are inferred from vocabulary
and marked with a trailing `(i)`. Good enough to sort and filter, not to cite.

## The scripts (`pipeline/`)

Run in this order. Every text value each writes is a verbatim quote that carries
its source page.

| Script | What it does | Why |
|---|---|---|
| `segment.py` | Splits the OCR text into documents and maps each to a spreadsheet row. | The package is one long scan; extraction needs document boundaries first. |
| `extract.py` | Pulls structured fields from a document's whitespace-normalised text. | OCR wraps headings across lines, so line-anchored patterns miss them. |
| `build_new.py` | Builds a workbook from a release that has no prior spreadsheet. | Same column set as a reconciled workbook, so releases concatenate. |
| `build_v2.py` | Fills an existing workbook: page anchors, quoted conditions, split units, resolved identifiers, a numeric queue. | Reconcile against the source without touching a cell that already holds a value. |
| `annotate.py` | Second pass: amendment rows, inferred classes, verification notes, a Discrepancies sheet. | A disagreement is recorded beside the original figure, never substituted for it. |
| `polish.py` | Refreshes the Overview stats and writes the Methodology sheet. | The workbook states how it was built. |
| `make_overviews.py` | Writes a per-folder HTML overview and a root index. | A reader checks a row against a page without opening the PDF. |
| `build_guidebook.py` | Indexes a technical guidebook: numbered sections and the guidance modality. | A guidebook needs a different schema but the same page-cite rule. |

The `_pdf_v2/` and `_pdf_v3/` folders hold an earlier copy of the pipeline and a
separate LLM multi-reader pipeline, kept as worked examples.

## Claude tooling (`.claude/`)

The multi-reader pipeline reads each document with a model instead of a regex.
Two readers read every document, and their agreement is the confidence signal.

| Agent | What it does | Why |
|---|---|---|
| `page-reader` | Reads one segmented document and records its fields against a staged contract. | A model reads a title line or a stamped figure that OCR breaks and a pattern misses. |
| `wave-orchestrator` | Spawns two `page-reader` agents per document and reports per-field agreement. | Two independent reads catch a single reader's error; agreement grades the row. |
| `labeller` | Sorts extracted values onto one controlled vocabulary, after extraction. | Classification stays separate from reading, so a label error cannot corrupt a quote. |

| Skill | What it does | Why |
|---|---|---|
| `spec-lint` | Reviews a field spec for questions two readers would answer differently. | An ambiguous question, not a weak reader, is the usual cause of disagreement, and it is cheaper to fix before a run. |
| `copy/plain`, `copy/humanize` | Project overlays for the report-writing skills: domain terms and banned constructions. | Delivered prose stays in one register for a consultancy audience. |

## Things that will bite you

**Bates numbers are not page numbers.** They run together for the first several
hundred pages of a package, then drift apart. Both are recorded for this reason.

**English-only OCR loses French documents entirely.** Accents vanish, so
`accordée à` stops matching, and the document is not flagged as missing — it is
simply invisible. Always pass every language present.

**Amendments share a file number with their parent.** Whether they get their own
row changes the row count, which matters when comparing totals with anyone else.
These scripts give them their own row and mark `Record_Type`.

**Some blanks are permanent.** Pages carry Access to Information exemptions —
s.19(1) for personal information, s.20(1)(b) and (c) for third-party commercial
information. A value withheld under the Act will never be recovered by reading
harder, so the row records which exemptions its pages cite.

**A release is not all authorizations.** Packages vary from dense stacks of forms
to mostly correspondence, compensation plans and reports. Row counts in the tens
from a 3,000-page package can be correct.
