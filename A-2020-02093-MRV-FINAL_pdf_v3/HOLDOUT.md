# The holdout, scored once

Scored 2026-09-02, against the workbook this pipeline rebuilds, on the 46 file
numbers of the holdout half of `split.json`. The tuning half is scored freely; this
was read once and is not scored again. Any later number is a different measurement
and has to say so.

Corpus: 129 documents, 516 reads, 121 rows, 5,814 conditions, `qc.py` exit 0.

## Agreement

| field | agrees | wrong | withheld | of cells |
|---|---|---|---|---|
| `date_of_issuance` | 40 | 4 | 0 | 91% |
| `proponent` | 33 | 13 | 0 | 72% |
| `province` | 45 | 1 | 0 | 98% |
| `hadd_destruction_m2` | 16 | 5 | 1 | 73% |
| `hadd_alteration_m2` | 13 | 0 | 3 | 81% |
| `hadd_disturbance_m2` | 5 | 0 | 2 | 71% |
| `impact_other_units` | 2 | 2 | 9 | 15% |
| **TOTAL** | **154** | **25** | **15** | **79%** |

The tuning half, measured the same day, is 77% over 194 cells. The holdout scoring
two points **higher** than the half the rules were built on is the result this
split exists to test for, and it is the one worth reporting: no rule here was
fitted to the documents it was measured on.

## What the number is not

**Two of the seven columns are not measuring what they appear to.**

`proponent`, at 72%, is mostly not disagreement. Twelve of its thirteen misses are
the same body written two ways -- `DFO Small Craft Harbours` against
`Department of Fisheries and Oceans, Small Craft Harbours`, `NB Department of
Transportation and Infrastructure` against `New Brunswick Department of
Transportation and Infrastructure`, `Municipalite de Sacre-Coeur` against
`Municipalité de Sacré-Cœur`. The extraction quotes the document; the prior
workbook uses a person's shorthand. Scored on meaning rather than string equality
this column is near the high nineties, and the spec already says label columns
must be measured that way. This is a quoted column and was not.

`impact_other_units`, at 15%, is nine withheld against two wrong. Withholding is
the designed outcome for a field the readers could not agree on, and it counts in
the denominator, so the column reports the rule working as a failure. Two wrong out
of four answered is what it actually says about the values that were filled.

**One cell rests on a test value the release contradicts.** `18-HCAA-00064`
`hadd_destruction_m2`: the workbook's 4,037 m2 includes a 3,250 m2 figure belonging
to another field, and the extracted 787 is right. Counted wrong here and reported
rather than subtracted -- a scorer that drops the cells it disagrees with measures
nothing. It is 1 of the 25 disagreements.

## Quote verification, all fields, both readers

| | | |
|---|---|---|
| pass | 2,563 | 62.3% |
| null | 1,435 | 34.9% |
| REJECT | 56 | 1.4% |
| QUEUE | 54 | 1.3% |
| MALFORMED | 8 | 0.2% |

Verification was run before the page-break allowance was extended to fields, which
gained 47 entries a pass and lost none. None of the 47 is in a column this score
measures, so the figures above stand as scored.
