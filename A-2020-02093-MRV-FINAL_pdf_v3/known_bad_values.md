# Known-bad values in the prior workbook

The prior workbook is the test set. Scoring against an uncorrected test set puts a
ceiling on the result that is not the extractor's fault, so the values recorded here
are resolved by hand before the holdout is scored.

Each entry states what the release says, on which page, so the resolution can be
checked rather than taken on trust.

## 18-HCAA-00233 — date of issuance

| | |
|---|---|
| Prior workbook | `2020-12-07` |
| Extracted | `2020-01-10` |
| Release pages | 92-102 (Belleville, Catharine St. Pedestrian Bridge, Moira River) |

**Both dates are in the release, and they contradict each other.**

The authorization's own issuance stamp, on release page 98, reads `JAN 1 0 2020`.
The OCR text layer renders it `JAN 10 20271`, which is why it cannot be settled from
the text layer alone; the scan is legible and unambiguous.

The amendment letter that follows it, dated March 8 2021 on release page 99, refers to
"your authorization issued under paragraphs 34.4(2)(b) and 35(2)(b) of the *Fisheries
Act* also acting as a permit under the *Species at Risk Act* on **December 7, 2020**."

So the extracted value is a correct transcription of the stamp, and the workbook value
is a correct transcription of the amendment letter. Neither is a misreading. What the
release does not settle is which document the row is keyed to: a stamp reading January
10 2020 and a letter describing an authorization issued December 7 2020 cannot both
describe one issuance.

This is a property of the source, and it belongs on `Discrepancies` with both pages.
The decision it asks of a person is which document the `18-HCAA-00233` row represents,
not which figure is typed correctly.

## Alteration area whose components do not sum to the recorded figure

Not yet resolved. The file number is identified by `build.py`'s own sum check, which
records a stated total its components do not reach; resolving it needs the clause and
the workbook cell side by side.
