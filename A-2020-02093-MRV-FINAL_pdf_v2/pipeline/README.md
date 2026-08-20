# Extraction pipeline

Rebuilds the filled columns of `DFO_2021_FAA_offsetting_summary_WORKING_v2.xlsx`
from the OCR text of `A-2020-02093-MRV-FINAL.pdf`.

## Requirements

`openpyxl`, plus the OCR sidecar `A-2020-02093-MRV-FINAL_OCR_engfra.txt`
(produced by `ocrmypdf --language eng+fra --sidecar ...`).

## Run

The build only fills empty cells, but it appends rows and rewrites
`Source_Reference_ID`, so start from a clean copy of the prior workbook:

```
cp "DFO_2021_FAA_offsetting_summary_WORKING_thru_Part22 1.xlsx" \
   DFO_2021_FAA_offsetting_summary_WORKING_v2.xlsx
python segment.py A-2020-02093-MRV-FINAL_OCR_engfra.txt segs.json
python build_v2.py A-2020-02093-MRV-FINAL_OCR_engfra.txt segs.json
python annotate.py A-2020-02093-MRV-FINAL_OCR_engfra.txt segs.json
python polish.py
```

## What each step does

- `segment.py` — finds each authorization's title page and slices the PDF text
  into one segment per document, recording page range, Bates range and the
  PATH/SAPH identifier stamped on the document's own first page.
- `extract.py` — pulls the numbered condition sections (contingency, monitoring,
  offsetting), the impact clause and the front-matter fields out of one segment.
  Handles both the English and French forms of the authorization template.
- `build_v2.py` — maps workbook rows to segments, fills empty cells with verbatim
  quotes, splits the offsetting amounts into value and unit, appends
  authorizations that have no row, and writes the `Numeric_Review_Queue` sheet.
- `annotate.py` — adds amendment rows, infers classifications, records redaction and
  derivation notes, and writes the `Discrepancies` sheet.
- `polish.py` — refreshes `Overview` and rewrites `Methodology`.

Area figures are never written automatically; see the `Methodology` sheet.
