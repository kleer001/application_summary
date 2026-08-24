# Adjudicator contract — pass C

Two readers read one document without seeing each other's answers and gave
different answers for one field. Mechanical rules have already settled the cases
where they said the same thing at different lengths, or where one listed fewer
items than the other. What reaches you is what those rules could not settle.

Your job is to read the pages and decide which answer the document supports.

## What you are given

The document's text excerpt, the same pages as a PDF, the field's definition,
and both answers with the quotes and pages each reader cited.

## The decision

Read the cited pages. Then choose exactly one of:

- **`"1"`** — reader 1's answer is what the document says.
- **`"2"`** — reader 2's answer is what the document says.
- **`"both"`** — the document says both, and each reader found part of it. This
  is the common case for a field that can hold several items: two readers each
  took a different subset of one list. Give the combined answer.
- **`"neither"`** — the document supports a third answer that neither reader
  gave. Give it, with its quote and page. `neither` always carries entries: it
  names a better answer, so there is always something to quote. Where your
  conclusion is that the document states nothing for this field — both readers
  quoted figures belonging to other fields, say — that is not `neither` but
  `absent`, which is the only verdict that empties a cell.
- **`"unresolved"`** — the pages do not settle it. Say what would.

`unresolved` is a real answer and not a failure. A field whose definition admits
two readings will produce two defensible answers forever, and recording that is
more useful than picking one. But do not reach for it to avoid reading: a
disagreement about what is printed on a page is settled by the page.

## The rules that bind you

**Every value you return carries its own quote and page**, exactly as the
readers' did, and is checked the same way. An adjudicated answer that cannot be
found on the page it cites is discarded like any other.

**The document's own words, in the document's own language.** You are choosing
between readings, not improving them. Do not tidy a quote, translate it,
summarise it, or convert a schedule into a duration.

**A number is not a preference.** Where two readers give different figures, one
of them is on the page and one is not, or they are figures of different things —
a total against its components, what is required against what is offered. Say
which, and quote the sentence that draws the line.

## A different question: is this number a condition, or a heading?

Some briefs ask this instead. One reader recorded a numbered line as a condition;
the other passed over it as a heading for the numbers beneath it. Both read the
same page. You are given the line's text, its children, and the pages.

**A condition is a specific individual deliverable** — a thing to be done,
submitted, built, monitored or stopped, that somebody could be held to. A line
that announces what is coming and leaves the doing to the numbers below it is a
heading, however it is phrased.

The word *shall* does not settle it. Umbrella lines are routinely written as
obligations and still impose nothing of their own:

> **5.2** List of reports to be provided to DFO: The Proponent shall report to DFO
> on whether the offsetting measures were conducted according to the conditions of
> this authorization by providing the following:
> > **5.2.1** A post-construction monitoring report ... shall be submitted to DFO by
> > March 31, 2022.
> > **5.2.2** Offsetting monitoring reports shall be submitted to DFO after each year
> > of monitoring by December 31 (2022, 2023, 2024, 2025, 2026).

`5.2` is a **heading**. It says reports will be provided and then points at the
list; 5.2.1 and 5.2.2 are the deliverables, each with its own report and its own
date. Nothing is lost by dropping 5.2, and that is the test.

The test is not whether the line reads like an obligation but whether **dropping
it would lose a deliverable that is not already stated beneath it**. Where the
parent binds something its children do not — a deadline that governs all of them,
a standard they must all meet, a report the children never name — it is a
condition and the children are conditions too.

One numbered line can hold more than one deliverable: two reports on different
dates written into a single number. That does not make it a heading. Record it as
the one entry its number gives it, and say in your reason that it carries more
than one, so the count is known to understate it.

For these briefs `winner` is `"condition"` or `"heading"`, or `"unresolved"` if
the pages genuinely do not settle it. `entries` stays empty: nothing is being
re-quoted, the number is being kept or dropped.

## A third question: what does the page say?

Some briefs carry no two answers to choose between. They carry a `question`
naming what is missing, and reach you because nobody produced a quote that
verified against the pages it cited. Read the pages and answer the question
directly — this is a reading, not a choice.

**Neither reader verified this field.** The brief gives both readers' rejected
answers so you can see what was tried. They are not candidates: a quote that
failed verification is a quote the pages do not carry as written. Read the pages
and record what the document says for this field, with your own quote and page.
Where the document is silent, that is `absent`, and it is a real answer — many
fields do not appear on many forms.

**A condition's text is not on the page it cites.** The brief gives the number
and the condition as each reader wrote it down. Three things are worth checking
in this order: whether the text is on a nearby page, because a page number read
off a running header lands a line or two out; whether the text layer mangled it,
in which case the scan carries it and the excerpt does not; and whether the text
is a reader's paraphrase rather than the line as printed. Record the condition
as the scan shows it, with the page it is actually on.

For these briefs `winner` is one of:

- **`"found"`** — the document does carry it. Give it in `entries`, quoted from
  the page it is really on.
- **`"absent"`** — the pages do not carry it. `entries` stays empty. For a field
  this means null; for a condition it means the entry should not be in the
  workbook.
- **`"unresolved"`** — the pages do not settle it. Say what would.

## Output

Write a single JSON file to the path you are given:

```json
{"document_id": "<id>", "field": "<field name>",
 "winner": "1|2|both|neither|unresolved|condition|heading|found|absent",
 "reason": "<one or two sentences, naming what on the page decided it>",
 "entries": [{"value": ..., "quote": "...", "page": <n>, "source": "text|image|both"}]}
```

`entries` is the answer you are certifying — empty for `unresolved`, for
`absent`, and for the condition-or-heading briefs, where nothing is being
re-quoted. Pages are numbered from 1, as in the excerpt and the PDF beside it.

Take the vocabulary from the section that matches your brief: `1`/`2`/`both`/
`neither` for two answers, `condition`/`heading` for a disputed number,
`found`/`absent` for a brief carrying a `question` and no candidates.
`unresolved` is available to all three.
