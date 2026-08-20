---
name: spec-lint
description: Review a field specification for defects that make two competent readers disagree, before spending a run on it. Use when writing or revising the question list for a structured-extraction job, when independent readers disagree on a field, or when extraction output is inconsistent across documents in a way that looks like reader error but may be an ambiguous question.
---

# Linting a field specification

A field specification is a list of fields, each with a question describing what
to extract from a document. Most disagreement between two competent readers is
not reader error — it is a question that admits two defensible answers.

Run this before committing a run. A defective question wastes the whole run and
the disagreement it produces is uninterpretable: you cannot tell a bad reader
from a bad question after the fact.

## How to use this

**Pass 1 — static.** Read the specification alone against Part A. Each check is
answerable without running anything.

**Pass 2 — empirical.** Run two independent readers on one document. Part B maps
disagreement patterns to the defect that caused them. This catches families no
static list names, so do it even when Part 1 comes back clean.

**Triage rule.** When two readers disagree, ask whether both answers are
defensible readings of the question. If yes, the specification is at fault. If
one answer is merely incomplete or wrong, the reader is. Fix specifications
first — reader failures measured against a defective question mean nothing.

---

## Part A — static checks

### A1. Double-barrelled
One field asking two independent questions. Readers answer one, the other, or
concatenate.
*Signal:* the question joins two concepts with "and" that could each stand alone.
*Fix:* split into two fields.

### A2. Aggregation unspecified
A quantity field where the document states several values and the question does
not say whether to sum them, list them, or take the largest.
*Example:* "disturbance area" against text listing 50 ha in zone A, 30 in B, 20 in C.
*Signal:* a numeric field whose question lacks "total", "each", or "largest".
*Fix:* ask for components with individual citations, and a total only where the
document states one itself.

### A3. Temporal anchor missing
A date or period field that does not say which event anchors it.
*Example:* "effective date" against a document carrying an issue date, a validity
start, an amendment date, and a condition deadline.
*Signal:* a date field whose question does not name the event it belongs to.
*Fix:* name the event and the place on the document it is read from.

### A4. Multi-source tiebreak missing
A single-value field where the document plausibly offers several candidates in
different places, with no stated priority.
*Signal:* a scalar field whose subject appears more than once in a typical
document.
*Fix:* state the tiebreak — earliest, latest, the one in a named section.

### A5. Enum narrower than reality
Response options that omit values the documents actually contain. A yes/no where
the source says "conditional"; "named, or none identified" where the source says
"not likely to adversely affect".
*Signal:* the option list was written from expectation rather than from a sample
of real documents.
*Fix:* derive options from a sample, and provide an escape value.

### A6. Enum options overlap
Options that are not mutually exclusive, so one value fits two.
*Example:* "0–50 ha / 30–100 ha / 100+ ha".
*Signal:* list the options and look for a value satisfying two.
*Fix:* make boundaries exclusive and state which side is inclusive.

### A7. Unit of instance undefined
A counting or enumeration field that does not define what one instance is.
*Example:* "number of sites" where a site could be a parcel, an operational unit,
or a contiguous area — answers differ by an order of magnitude.
*Signal:* a field asking to count or enumerate without defining the unit.
*Fix:* define the unit, and where a document nests them, ask for every level with
its parent recorded so granularity is a query-time choice rather than the
reader's judgement.

### A8. Scope boundary undefined
Extraction "from the section on X" when a document holds several such sections,
or when layout makes the region's edges unclear.
*Signal:* the question names a region by topic rather than by identifier.
*Fix:* name the section identifier, or ask for every instance labelled by which
section it came from.

### A9. Synthesis and citation in one field
Asking for a summary while requiring a verbatim supporting quote. Structurally
unsatisfiable when the summary spans more text than any one quote covers.
*Signal:* the question uses both "summarise" and "quote" for one field.
*Fix:* separate them — short cited values in one field, full text elsewhere.

### A10. Presupposition
The question assumes a state that may not hold, so readers invent an answer or
report absence inconsistently.
*Example:* "when did construction restart" against a document describing a new
project; a field that exists only on one regional variant of a form.
*Signal:* the question would be unanswerable, rather than merely empty, on a
document lacking the assumed state.
*Fix:* say when the field does not apply, and give it a distinct null reason.

### A11. Conditional dependency unstated
A field that should only be filled when another field holds a value, without
saying so.
*Example:* an amount field that is meaningless unless the corresponding
requirement field is "yes".
*Signal:* two fields where one is a detail of the other.
*Fix:* state the dependency in the dependent field's question.

### A12. Missing-data states undefined
Treating every empty value as one thing. At minimum these differ: the document
never asks; it asks and nobody answered; the answer is withheld; the answer is
present but unreadable.
*Signal:* the output contract has one null and no reason code.
*Fix:* require a reason on every null. Without it, absence in the source cannot
be distinguished from extraction failure, and nothing can be counted.

### A13. Two reference systems for one identifier
The same thing addressable two ways, with no statement of which to use.
*Example:* page numbers both relative to an excerpt and absolute in the source.
*Signal:* an identifier that appears in two numbering schemes anywhere in the
inputs — including in the input files themselves, not just the question text.
*Fix:* one convention, stated. Convert downstream.

### A14. Relative and explicit forms both valid
A field satisfiable by either an anchored value or an offset.
*Example:* a deadline stated as "within 90 days of completion" or as "31 March
annually".
*Signal:* readers could return different types — a duration string and a date.
*Fix:* accept both and require a type tag, or say which form is wanted.

### A15. Vague quantifier without anchor
"Often", "significant", "nearby", "approximately" with no numeric threshold.
*Signal:* a frequency or magnitude word carrying no number.
*Fix:* anchor it, or ask for the document's own words verbatim.

### A16. Loaded framing
Evaluative language in a question steers the answer.
*Signal:* adjectives carrying judgement — "obvious", "significant", "adequate".
*Fix:* neutral wording. Note that this defect can *raise* apparent agreement:
two readers steered the same way agree while both being wrong, so agreement is
not evidence against it.

---

## Part B — empirical signals

Run two independent readers on one document and read the disagreement.

| What you observe | Likely defect |
|---|---|
| Answers are different *types* — a duration and a date, a number and a list | A14, A2 |
| Answers cluster in distinct groups differing by an order of magnitude | A7 |
| One answer is a strict subset of the other | reader incompleteness, not a spec defect |
| Both cite different sections, each internally consistent | A8, A4 |
| One reader reports a value, the other reports absence, repeatedly on one field | A10, A11 |
| Answers have no overlap at all | the question means two different things — A1 |
| Readers report "neither option matches" or invent an option | A5 |
| Disagreement concentrates at boundary values | A6 |
| Value is broader than the quote cited beside it | A9 |
| Two readers use different null markers for the same situation | A12 |
| Disagreement tracks document variant or region | A10 |
| Cited locations differ but quoted text is identical | A13 |

A field disagreeing on most documents in a batch is a specification defect until
proven otherwise, however plausible each individual answer looks.

---

## Sources

The families draw on annotation-guideline design and inter-annotator agreement
work in corpus linguistics, survey and questionnaire methodology, clinical case
report form design (the source of the missing-data distinctions), and
information-extraction evaluation. These fields have catalogued question-wording
failure for decades; most defects found in practice are already named there.
