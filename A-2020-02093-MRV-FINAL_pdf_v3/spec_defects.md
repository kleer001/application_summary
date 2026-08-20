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

What has to be decided is whether `Conditions` is a list of *obligations* or a
transcription of the document's *numbering*. Both are legitimate records and they
are not the same sheet. Until the contract says which, the count of conditions per
document is not a stable quantity.

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
