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
  gave. Give it, with its quote and page.
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

## Output

Write a single JSON file to the path you are given:

```json
{"document_id": "<id>", "field": "<field name>",
 "winner": "1|2|both|neither|unresolved",
 "reason": "<one or two sentences, naming what on the page decided it>",
 "entries": [{"value": ..., "quote": "...", "page": <n>, "source": "text|image|both"}]}
```

`entries` is the answer you are certifying — empty only for `unresolved`. Pages
are numbered from 1, as in the excerpt and the PDF beside it.
