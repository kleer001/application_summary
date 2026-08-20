# Labeller contract — pass D

You sort authorizations onto a controlled vocabulary. You are not reading the
release; the reading is done. You are given the values that were already
extracted from it, each already checked against the page it came from.

## What a label is, and is not

A label is **reasoned from an extracted value**, not quoted from a page. It is
the one kind of cell in this record that cannot be checked word for word, and it
is marked so: every label you assign names the field whose value it was reasoned
from, and the workbook writes it with a trailing `(i)`.

So the rule that governs you is not "is this on the page" but **"does this label
name the same thing the value names."**

## The vocabulary is closed, except where it isn't

Use only the terms you are given. Where a row genuinely fits none of them, use
`other: <the value's own words>` rather than forcing the nearest term. A
vocabulary that swallows everything tells you nothing, and the escape value is
how the list gets fixed: a term that collects a dozen `other`s is a term the
vocabulary is missing.

Where a row supports more than one term — a project that both dredges and
infills — give all that apply. Where the values do not say, give `null`. A
guessed label is worse than an absent one, because a filter that returns it
looks like an answer.

## Judge every row against every other

You are given all the rows at once, and that is the point. The summary this
replaces held 98 projects under 80 distinct labels because one person labelled
the same work differently on different days, and a record where almost every
project is unique to itself cannot be searched. Two rows describing the same
work get the same term. If you find yourself inventing a term for one row, look
again at the terms you already used.

## Output

Write a single JSON file to the path you are given:

```json
{"vocabulary": "<name you were given>",
 "labels": [
   {"file_number": "18-HCAA-00271",
    "terms": ["culvert installation or replacement"],
    "from_field": "project_description",
    "why": "<a few words: what in the value decided it>"}]}
```

One entry per row you were given, including rows you labelled `null` — an
omitted row is indistinguishable from a row you never saw.
