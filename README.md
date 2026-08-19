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

## Identifier formats

Two generations appear in these releases:

- `NN-HXXX-NNNNN` — current
- `NN-HXXX-PAN-NNNNN` — older, with an extra regional segment

Quebec documents also carry a provincial authorisation number
(`N° d'autorisation : YYYY-NNN`) and are sometimes identified by that alone.

The `HXXX` segment is the DFO region, and it maps onto provinces without
exception across the corpus this was built on:

| Code | Region | Provinces seen |
|---|---|---|
| HPAC | Pacific | British Columbia, Yukon |
| HCAA | Central and Arctic | Ontario, Alberta, Manitoba, Saskatchewan, Nunavut, Northwest Territories |
| HGLF | Gulf | New Brunswick, Prince Edward Island |
| HMAR | Maritimes | Nova Scotia |
| HNFL | Newfoundland and Labrador | Newfoundland and Labrador |
| HQUE | Quebec | Quebec |

`build_new.py` derives a `Region` column from this and flags any row whose
province falls outside its region.

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
