# Working in this repo

Extraction pipeline for scanned government release packages. See `README.md` for
what it produces and how to run it.

## The rule that governs everything here

**A filled cell must be checkable against a page number.** Every text value the
pipeline writes is a verbatim quote, and every row carries the page range it came
from. Before considering a change done, run the check that every quoted cell
still appears in the pages its own row cites. If that check does not pass, the
change is not finished.

```python
# the shape of the check: quoted value must occur in its cited page range
src = " ".join(pages[page_start - 1:page_end])
assert normalise(cell_value)[:60] in normalise(src)
```

## Never overwrite source data

Cells that already hold a value are left alone. Where extraction disagrees with
an existing value, both are kept — the original in place, the extracted figure in
an `Extracted_` column — and the disagreement is recorded on the `Discrepancies`
sheet. A run that silently replaces a regulatory figure is a bug even when the new
figure is better.

## Measure before believing a heuristic

Extraction accuracy is knowable here: values already present in a workbook are the
test set. Any change to a numeric rule gets measured against them before it stays.

Current agreement, against values already in the reconciled workbook:
destruction 76%, alteration 93%, disturbance 75%.

A rule that looks smarter and measures worse gets reverted. One such rule — drop
any figure whose removal leaves a sum stated elsewhere in the clause — took
overall agreement from 81% to 71% and is documented in `extract.py` so it is not
tried again.

## Extraction thresholds

Do not auto-fill a column whose measured agreement is below roughly 95%. Queue the
candidates with their source sentence instead. The queue is more useful than a
wrong number, because a wrong number in a compliance record has to be found before
it can be corrected.

Values reasoned from text rather than quoted from it carry a trailing `(i)`.

## Regexes go wide, then get measured

OCR output is not clean text. Patterns here tolerate what the scanner does to the
page: `m2` renders as any of `m2 m² m? m7 m* m° m' m’`, the digits `0` and `1`
appear as `O` and `l`, and words break mid-token (`AUTORISA TION`, `AL INÉAS`).
Anchor on structure — a labelled field, a numbered heading — rather than on an
exact phrase, and never on a title line.

Section headings are found by phrase with the number optional, because the number
is frequently lost. Bodies are sliced between consecutive headings.

## Language

Pass every language present in the package to OCR. A French document read with
English-only OCR does not fail loudly; it becomes unmatchable and silently absent
from the output. Patterns in `extract.py` and `segment.py` carry both the English
and French wording of each field, and tolerate accents being dropped.

## Adding support for a new release

1. OCR with every language present, keeping the sidecar text.
2. Run `segment.py` and compare its document count against a manual count of
   pages carrying an "issued to" block. A gap means the structural test needs
   widening, not that the documents are absent.
3. Check the first page of anything the segmenter missed. New identifier formats
   and new form wordings show up here first.
4. Only then build the workbook.

Widen a pattern to admit a real observed variant. Do not add a pattern for a
variant you have not seen in the text.
