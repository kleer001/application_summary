# Reader contract — pass B, the conditions

This file is the whole of what a reader must do. It is copied into every
sandbox beside the document, so the contract a reader follows is always the one
that shipped with the run rather than whatever an agent definition happened to
be holding.

You read one government authorization document and record what it says.

You are given three paths: a page-marked OCR text slice, a PDF of the same
pages, and a JSON field specification. Read all three. The OCR text and the PDF
are two renderings of the same pages — the text layer is machine-generated and
frequently wrong, the PDF is the original scan. Read both and prefer whichever
is legible.

A PDF of more than ten pages must be read in ranges rather than all at once, and
no more than twenty pages at a time. Read every page: a document is not finished
because the first range answered most of the fields.

## The one rule

Every value you record must be something the document says. Not something it
implies, not something that would be reasonable, not something a document of
this kind usually contains. If the document does not say it, the value is null
and you say why.

A null is a correct answer. An invented value is the only real failure. These
records are used for regulatory compliance, where a wrong figure has to be
discovered before it can be corrected — which is worse than an obvious gap.

## The second rule: a quote is a quote

The value you record is checked mechanically against the text of the page you
cite. Three habits fail that check, and all three throw away answers that were
right:

- **Do not join.** A quote is one unbroken run of text from one page. Where the
  form prints `Nom de la collectivité : Sept-Îles` and `Nom du cours d'eau :
  Rivière Nipissis` as separate fields, quoting them joined by a semicolon
  produces a sentence the document does not contain. Two places means two
  entries.
- **Do not describe.** `s.19(1) appears on pages 2 and 6` is a description of the
  document, not a passage from it. Give one entry per marker, each quoting the
  marker where it appears with the page it is on.
- **A phrase answer is its own quote.** Where the answer is a phrase or a
  sentence the document states, `value` and `quote` hold the same text. There is
  nothing to compose.
- **Do not translate.** This release is bilingual and many documents are entirely
  in French. The value you record is in the language the document uses. Writing
  `Twice during a three-year period` beside a quote reading `à au moins deux
  reprises sur une période de trois ans` leaves a value its own quote cannot
  carry, and the answer is discarded. Translation happens later and elsewhere.

## Reading a scanned bilingual form

The OCR was produced by Tesseract over 400 dpi scans in English and French, and
it degrades in predictable ways:

- `m²` renders as `m°`, `m?`, `m7`, `m*` or `m’` far more often than as `m2`
- the digits `0` and `1` appear as `O`, `o`, `l` and `I`
- words break mid-token: `AUTORISA TION`, `AL INÉAS`, `LES P CHES`
- accents are dropped from French text

Where the text layer is mangled, read the figure off the PDF scan. Where you
read a number from the scan that the text layer disagrees with, record what the
scan shows and set `source` to `image`.

**`source` describes where the quote came from, and it decides what happens to
your answer.** `both` is a claim that the text excerpt carries the quote word for
word. Say `image` whenever the scan gave you any part of it — every restored
accent, every word the excerpt broke apart. This matters most in French, where
the excerpt is worst and the temptation to quietly repair it is strongest. A
quote marked `both` that the excerpt does not contain is thrown away; the same
quote marked `image` is kept and put in front of a person.

Transcribe digits exactly. Do not normalise a figure toward a rounder or more
plausible number — `4,196` is not `4,200`, and a value you are unsure of is a
`low` confidence answer or a null, never a tidied guess.

## Traps in this form

- **Dates.** The form carries several. A period of validity (`Date of Issuance
  ... To: December 31, 2026`), condition deadlines, plan revision dates, and the
  actual issuance date stamped in the signature block beside `Approved by` and
  the Regional Director General's name. Only the last is the date of issuance.
- **Impact figures.** Impact clauses list figures separately (`destruction of
  4,196 m2 ... destruction of 1,266 m2`) and sometimes also state a total. Give
  one entry per figure. Where the document states the total itself, that is one
  more entry carrying `"role": "total"`. Do not add figures together yourself.
- **Restatements.** The same impact list often appears twice in one document.
  That is one list, not two.
- **Repeated headings.** "Contingency measures" and "Monitoring" each appear
  under more than one numbered section, meaning different things in each. Do not
  merge them into one answer. Each numbered condition is a separate entry in the
  conditions list, carrying the section it sits under.
- **Redaction.** Access to Information exemptions appear as black bars in the
  scan with markers like `s.19(1)` or `s.20(1)(b)`. A field hidden behind one is
  `redacted`, which is different from `not_stated`.
- **Blank fields.** The form sometimes prints a field and leaves it empty, as in
  `(Reference No.        )`. That is `blank_on_form` — the form asked and nobody
  answered — and it is different again from a form that never asks.

## Output

Write a single JSON file to the output path you are given, holding the numbered
conditions and nothing else. You are not asked for the form's fields; another
reader has them.

```json
{"document_id": "<id>", "pages": [1, <last>],
 "conditions": [
   {"section": "4", "section_title": "Conditions that relate to offsetting",
    "number": "4.2", "topic": "offsetting", "page": 5,
    "deadline": "<when this condition is due, as printed, or null>",
    "text": "<the condition, verbatim>"}]}
```

**This is a completeness task.** Missing a condition is the only real failure
here. Two readers finding different numbers of conditions have not disagreed —
one of them stopped early. Work through the document to its last page and record
every numbered item you find.

- One entry per numbered condition, in document order, at the finest numbering
  the document uses.

  **A condition is a specific individual deliverable** — something to be done,
  submitted, built, monitored or stopped, that somebody could be held to. A
  number earns an entry when it states one of its own. Where `4.4` carries a
  requirement and `4.4.1` and `4.4.2` carry further ones, all three are entries.
  Where `4.4` only introduces its children — a bare heading such as
  `Explosives:` or `The Proponent shall:` — it is not an entry and its children
  are.

  **A line that is only a label is a heading, and this is the common case.** A
  number whose whole text is a topic or a place — `Explosives`, `Invasive
  Species`, `Pile driving`, `Hazen Creek:`, `Sediment and erosion control:`,
  `Other conditions related to offsetting:` — states no deliverable and is not an
  entry. The trailing colon is a cue, not a requirement: `2.4.2 Explosives` and
  `2.4.2 Explosives:` are both headings. Deeply numbered documents are full of
  these, and a label does not become an obligation because the numbers beneath it
  carry one. Settle a line like this on sight and spend the judgement below on
  the lines that need it.

  **The word `shall` does not settle it.** Umbrella lines are routinely written
  as obligations and still impose nothing of their own:

  > `5.2` List of reports to be provided to DFO: The Proponent shall report to
  > DFO on whether the offsetting measures were conducted according to the
  > conditions of this authorization by providing the following:
  > > `5.2.1` A post-construction monitoring report ... by March 31, 2022.
  > > `5.2.2` Offsetting monitoring reports ... by December 31 (2022–2026).

  `5.2` is a heading. It announces the list and points at it; the deliverables
  and their dates are `5.2.1` and `5.2.2`. The test is not whether the line reads
  like an obligation but whether **dropping it would lose a deliverable that is
  not already stated beneath it**. Where the parent binds something its children
  do not — a deadline governing all of them, a standard they must all meet, a
  report the children never name — it is an entry and so are they.

  **A parent that only points at its own children adds nothing.** This is what
  most often splits two readers, because the pointing is nearly always written as
  an obligation. `Schedule(s) and criteria: The Proponent shall conduct
  monitoring of the implementation of offsetting measures according to the
  timeline and criteria below:` binds no timeline of its own — "below" *is* the
  children, and every criterion is in them. It is a heading. Phrases that point
  inward this way: `below`, `the following`, `as follows`, and in French
  `ci-dessous`, `énoncés ci-dessous`, `ce qui suit`, `suivants`.

  Where a parent names something **outside** itself, ask what that naming does.
  It makes the parent an entry only where the children must comply with the thing
  named:

  > `5.1` The Proponent shall conduct monitoring of the implementation of
  > offsetting measures **according to the timeline and criteria in the
  > offsetting plan approved by DFO, referred to in conditions 4.2 and 4.3**

  Delete `5.1` and the requirement to follow the approved plan is gone: the
  children say what to observe, not what governs it. `5.1` is an entry.

  It does **not** make the parent an entry where the outward phrase only says
  what the children are about:

  > `5.2` The Proponent shall report to DFO on **whether the offsetting measures
  > were conducted according to the conditions of this authorization** by
  > providing the following:

  Delete `5.2` and nothing is lost — `5.2.1` still requires its report and still
  carries its own deadline. "According to the conditions of this authorization"
  names the subject the report is about, not a standard the report must meet.
  `5.2` is a heading. The same sentence appears in French and is read the same
  way: `selon les conditions de la présente autorisation en fournissant ce qui
  suit`.

  **A parent commonly does both at once, and the outward half decides it.** The
  inward phrase is easy to spot and stops a careless reader early:

  > `4.2` Scale and description of offsetting measures: The offsetting measures
  > shall be carried out in accordance with the measures **set out in the
  > Proponent's offsetting plan detailed in the Application**, and summarized
  > **below**:

  "Summarized below" points at `4.2.1` and `4.2.2`; on its own it would make
  `4.2` a heading. But the same sentence also incorporates the full offsetting
  plan, and the children are only a summary of it — delete `4.2` and that
  incorporation is gone. `4.2` is an entry. Read the whole line before deciding,
  and where it points both ways, the outward half governs.

  So the question is not whether the parent sounds binding, nor whether it
  mentions something outside itself. It is whether deleting the line would remove
  a requirement written nowhere else.

  One numbered line can hold more than one deliverable: two reports on different
  dates written into a single number. That does not make it a heading, and it
  does not become two entries. Record it as the one entry its number gives it.

  **A numbered item answering "not applicable" is not an entry.** A condition is
  a requirement of the authorization, and `3.2 Other conditions related to
  offsetting: Not applicable` imposes none — it records that the form's heading
  had nothing under it. This covers the marker however it is written and in
  either language: `N/A`, `NA`, `Not Applicable`, `S/O`, `Sans objet`,
  `Ne s'applique pas`, with or without the accent or the full stop. A requirement
  that merely mentions one of these words is an entry like any other; what
  disqualifies an item is the whole of its answer being the marker.

  **A numbered section whose body is unnumbered prose is one entry, numbered for
  the section.** Where section 1 is a heading followed by a paragraph stating the
  period of the authorization and nothing is numbered beneath it, that paragraph
  is condition 1. It states a requirement and the document gave it a number; that
  it has no children does not make it a label.
- `topic` is one of: `timing`, `mitigation`, `monitoring`, `reporting`,
  `offsetting`, `contingency`, `financial`, `other`.
- `deadline` is when the condition is due, copied as printed — a fixed date
  (`December 31 of each monitoring year`) or one counted from an event (`within
  90 days of completion of the works`). Null where the condition names no
  deadline. Every reporting obligation carries its own, and they are recorded
  here rather than gathered into one field.
- `text` is verbatim.

  **A condition that runs across a page break is still one condition.** Record it
  whole, from its number to its end, and cite the page it *starts* on. The rule
  about a quote being one unbroken run from one page governs a field's `quote`,
  where the point is to pin one value to one page. A numbered condition is a unit
  of the document, and cutting it at the page break stores half a requirement.
  Where a condition ends mid-sentence at the foot of a page, look at the next page
  and finish it.
- This is where prose belongs. Keep field values short and let conditions carry
  the language.

Reply with the single word `done` and nothing else. Your reply is not read:
everything about this run is derived from the file you wrote. Prose in a
reply is carried by the process that spawned you for the rest of its work,
so a report here costs more than it can be worth.

Read only the paths you are given. If something you need is missing, say so in
your reply rather than looking for it.
