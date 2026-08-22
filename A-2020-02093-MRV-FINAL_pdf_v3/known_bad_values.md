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

## 18-HCAA-00145 — alteration area, stated total against its own breakdown

**Resolved: the source document is inconsistent, and the stated total stands.**

Page 2 of the authorization reads:

> Permanent alteration of a total of 2,363 m² of fish habitat due to the
> installation of temporary rock causeways for a duration of 6 months per
> construction year (Year 1: 779 m², Year 2: 1057 m², Year 3: 227 m²) in the
> Grand River.

779 + 1057 + 227 is 2,063. The authorization as issued disagrees with its own
parenthetical breakdown by 300 m². Nothing was misread: one reader took the
stated total, the other took the total and the yearly figures, and both quoted
the page correctly.

The recorded figure is **2,363 m²**, the total the document states, because the
rule is to quote what the document says and never to add figures together. The
300 m² gap is a property of the record, not of the extraction, and correcting it
here would put a number in the workbook that appears nowhere in the release.

The two culvert extensions on the same page — 32.5 m² and 10.8 m² — are separate
bullets describing separate alterations and are correctly not part of the 2,363.

## Other stated totals that do not match their components

Found by the same sweep. None is the case above; each is an extraction question
for pass C rather than a defect in the source.

| document | field | stated total | components sum to | what it looks like |
|---|---|---|---|---|
| `18-HQUE-00300_612` a2 | disturbance | 56,555 | 113,110 | exactly twice the total — every component recorded twice |
| `18-HCAA-00064_686` a1 | destruction | 787 | 4,037 | 537 + 250 is 787; a third figure of 3,250 belongs to another field |
| `14-HGLF-00267_1342` | destruction | 37,000 | 19,200 (a1) / 54,400 (a2) | the two readers found different component sets; the prior workbook records 19,200 |
| `18-HCAA-00145_415` a2 | alteration | 2,363 | 2,106.3 | the case above, plus the two culvert bullets |
