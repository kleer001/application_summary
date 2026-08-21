# Specification defects found by reader disagreement

Disagreement between two independent readers is the specification linter. Where
both answers are defensible readings of the field, the specification is at fault
and belongs here. Where one answer is merely incomplete, the reader is, and it
does not.

Each entry names what the readers did, so the fix can be checked against real
output rather than argued in the abstract.

## contract_b: whether a "Not Applicable" numbered item earns an entry

Numbered items reading `Not applicable` / `Not Applicable` / `NA` / `Ne s'applique
pas` appear throughout the release — typically at 3.2, 4.1, 4.7, 4.8, 4.9, 5.3.

Readers split on them, and both cite the contract:

- **Excluded**, on the rule that a number earns an entry only when it states a
  requirement of its own, and `Not Applicable` states none.
- **Included**, on the completeness rule, which says pass B is an enumeration task
  and a reader that drops numbered items has stopped early.

Both are defensible readings, so this is a defect in the contract rather than a
lapse by either reader.

Measured on `18-HCAA-00852_1821`, where the two readers returned **56 and 59**
conditions: the difference is exactly the three items answering "Not applicable"
at 3.2, 4.8 and 5.3, one reader naming them as excluded for stating no obligation
and the other naming them as included for completeness. Neither misread the page.

It matters more than it looks. Pass B combines by **union**, so an item one reader
includes survives whatever the other did. The effective behaviour is therefore
"included" no matter which reading is more common — the disagreement does not
surface as a conflict, it silently resolves in one direction.

**Settled: conditions are requirements of the authorization.** `Conditions` is a
list of obligations, not a transcription of the document's numbering, so an item
answering "not applicable" is not one. `contract_b.md` now says so, and
`combine.py` applies it to every read rather than relying on each reader to.

Applying it downstream is what makes the ruling reach the reads already banked.
The union kept a not-applicable item whenever either reader recorded one; the
filter drops it whichever reader recorded it, so the count no longer depends on
which reader was more literal and nothing has to be read again.

Measured over the reads banked so far: 29 entries across 18 distinct wordings are
the marker and nothing else, in both languages and with the accent and the full
stop coming and going. The workbook goes from 2348 conditions to 2326; rows,
decisions and discrepancies are unchanged. On `18-HCAA-00852_1821`, the document
this entry was written from, the two readers go from **56 and 59** to 56 and 56,
and the three items that separated them are exactly the three not-applicable
answers at 3.2, 4.8 and 5.3.

## contract_b: whether a number that both states a requirement and introduces
children earns its own entry

The same split, narrower. Readers agree that a bare label introducing children is
not an entry, and that a leaf stating an obligation is. They disagree on the case
in between — a number carrying its own requirement *and* numbered children beneath
it, such as an offsetting clause that both binds the proponent to a dated plan and
enumerates the measures in that plan.

Some readers record the parent and its children; others record only the children,
treating the parent as a heading. The contract's rule that "a number earns an entry
when dropping it would lose a requirement" settles this in principle, but readers
do not apply it consistently, which is the signal that it is not stated plainly
enough to survive contact with the forms.

**Open.** The ruling that conditions are requirements decides this case too — a
parent stating a requirement of its own is one, and a bare label is not — but
unlike the not-applicable question there is no way to apply it to reads already
taken. Whether a parent carried its own requirement is not recoverable from the
entry a reader chose to write; only re-reading settles it. So the wording is left
alone until the re-read, rather than changed now and quietly disagreeing with
every read banked under it.

## contract_a: `source` asserts something nothing can check

Every entry carries `source: text|image|both`. `both` asserts the reader
corroborated its answer against the scan. Nothing verifies that assertion, and
the failure it hides is real: a read whose PDF render had errored recorded
`both` on all 35 of its entries and answered from the OCR layer alone.

Measured over the pass-A reads banked so far — 88 reads, 3390 entries:

| claim   | entries |
|---------|---------|
| `both`  | 2846 |
| `image` | 529 |
| `text`  | 15 |

The claim can be confirmed but not refuted. A quote that is *not* in the OCR
layer proves the reader used the scan, and 69 of 88 reads carry at least one.
The absence of such a quote proves nothing: it is equally what a clean page
looks like. Fourteen reads claim `both` on every entry, and of those only three
carry no positive sign of the scan — and one of the three is from a run where
the scan was demonstrably rendered, because the driver's own transcript shows
the page images coming back.

So a read that answered from text alone while claiming corroboration cannot be
picked out of the corpus after the fact, and re-reading on suspicion would mean
re-reading reads that are fine.

**The field is a reader's annotation and is not evidence.** Do not gate anything
on it, do not report it as provenance, and do not use it to decide what to
re-read. What actually holds the line is upstream and mechanical: a night that
cannot render the scans refuses to read at all, and every quote is checked
against the page it cites whatever the reader says about where it came from.
