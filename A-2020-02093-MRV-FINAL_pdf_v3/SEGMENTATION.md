# How a document gets its file number, and how that goes wrong

The file number is the row key. Every value and every condition a document
contributes is filed under it, so a wrong number does not produce a wrong cell —
it produces a row nothing can find and conditions belonging to nobody. The
failure is silent in the extraction and loud only in `qc.py`, which is why the
checks below exist.

`segment.py` reads the OCR text layer and votes on the file numbers it finds
across a run of pages. Readers are given the scan as well as the text, so where
the two disagree it is usually because the text layer lost something the scan
still shows.

## The text layer sometimes has no header at all

`17-HQUE-00333_465` is the worked case. Page 1 of that document runs from the
title straight to `Autorisation délivrée à :` — the whole header block, file
number included, is missing from the text. The segmenter found no header, and
keyed the segment on the only file number appearing anywhere in its eight pages:
a parenthetical on page 5 citing a **separate 2018 offsetting agreement**,
`(n° référence MPO : 17-HQUE-00333)`.

Both readers, working from the scan, quote the real field: `N° du SAPH :
19-HQUE-00309`. Measured across every document read, the readers confirm the
segmenter 43 times, contradict it once, and never contradict each other — so
where both agree on a different number, they are seeing something the segmenter
could not.

Such cases go in `corrections.json`, keyed by stem, with the evidence. They are
**not** edited into `segs.json`: segmentation is regenerated, and an edit to its
output would be lost the next time without trace. `ids.corrected()` applies them
and `build.py` calls it wherever a row key is decided.

## A key that is not a file number

Two segments are keyed on an authorization number rather than a file number,
because OCR left nothing else on the page to key on:

| keyed as | pages | what is in the text layer |
|---|---|---|
| `Auth 2019-039` | 189–198 | `N° du SAPH : 19-HQUE-O00255` — garbled, and rejected as malformed |
| `Auth 2020-001` | 258–265 | no `SAPH` line at all; only `N° d'autorisation : 2020-001` |

`wave.check_keys` refuses to stage either, and says so by name. Neither has been
read yet, so neither number is confirmed; recovering them means reading the scan
and then adding a correction. Do not guess `19-HQUE-00255` from the garbled line —
the digit count is wrong in the OCR and the scan is the only authority.

## The trap: an amendment carries two file numbers

An amending authorization prints both, and the **running header on later pages
carries the amendment's number, not the authorization's**:

```
Authorization PATH No.: 18-HCAA-00192      <- page 1, the row key
Amendment PATH No: 20-HCAA-01023           <- page 1
PATH No.: 20-HCAA-01023                    <- pages 2, 3, 4, 5, 6, 7 ...
```

Any rule of the form "the file number appearing most often is the document's"
gets every amendment in the release wrong, and looks right on everything else.
The segmenter does not use that rule. Do not introduce it: the header on page 1
labelled *Authorization* is the key, and a bare `PATH No.` in a running header is
evidence of nothing on its own.

A single vote is likewise not a defect. Many of these forms print the number once
on the cover and never again, so a segment keyed on one occurrence is ordinary;
60 of 129 segments look like that and only one of them is wrong.
