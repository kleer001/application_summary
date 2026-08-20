# Reader contract — pass A, the fields

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
  sentence the document states, `value` and `quote` hold the same text,
  character for character. There is nothing to compose and nothing to shorten.

  Writing `Development of the open pit mine` beside a quote reading `The
  development of the open pit mine, which will cover 145 ha and be 300-370 m
  deep at its ultimate extent` is not a shorter answer, it is a summary — and a
  summary is the one thing this record cannot hold, because nobody downstream
  can tell it from the document's own words. Where a clause is long, the whole
  clause is the value.
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

Write a single JSON file to the output path you are given. **Every field has the
same shape: a list of entries.** There is no other shape, and nothing is recorded
anywhere except inside an entry.

```json
{"document_id": "<id>", "pages": [1, <last>],
 "fields": {
   "waterbody": {"entries": [
      {"value": "Rivière Nipissis", "quote": "Nom du cours d'eau ou du plan d'eau : Rivière Nipissis",
       "page": 1, "source": "both", "confidence": "high"},
      {"value": "ruisseau sans nom", "quote": "le libre passage du poisson dans le ruisseau sans nom",
       "page": 5, "source": "both", "confidence": "high"}]},

   "hadd_destruction_m2": {"entries": [
      {"value": 4196, "quote": "destruction of 4,196 m2 of fish habitat", "page": 2,
       "source": "both", "confidence": "high"},
      {"value": 1266, "quote": "destruction of 1,266 m2 of riparian habitat", "page": 2,
       "source": "both", "confidence": "high"},
      {"value": 5462, "quote": "for a total of 5,462 m2", "page": 2,
       "source": "both", "confidence": "high", "role": "total"}]},

   "authorization_number": {"entries": [], "reason": "not_stated"}}}
```

- **One entry per thing the document says.** A field the document answers once
  has one entry. A field it answers three times has three. A field it does not
  answer has none.
- **No entries means null, and `reason` is then required**: `not_stated` (the
  form never asks), `blank_on_form` (it asks and nobody answered), `redacted`,
  `illegible`. Recording no entries while quoting a figure elsewhere is the one
  contradiction that is never accepted.
- **`role`: `"total"`** marks a figure the document itself presents as the sum of
  the others. Never add figures up yourself to produce one. Without a stated
  total there is simply no entry carrying that role.
- `value` is the answer as the document gives it. `quote` is the text you read it
  from. `page` is the `=== page N ===` number that quote appears on — pages are
  numbered from 1 and the PDF beside the excerpt holds the same pages in the same
  order, so there is only one number to cite.
- **Every entry is checked mechanically**: its quote must occur on its page, and
  a numeric value's digits must appear in its own quote. An entry that fails is
  discarded, and a field is only as good as its entries.
- **A quote is one unbroken run of text from one page.** Do not join passages from
  two places, and do not repair what the scanner did to the words inside one.
  Where the OCR reads `Approved by: David` on one line and `David Nanang` on the
  next, quote the line carrying the name. Stitching them into `Approved by: David
  Nanang` produces text the document does not contain, and a right answer is
  thrown away for it. Two places means two entries.
- Your `value` must be carried by the quote beside it. A value broader than its
  own quote is the failure this check exists to catch.
- **An example in a field's definition shows the shape, not words to supply.**
  Where a definition illustrates a species as `Channel Darter (Percina
  copelandi), Lake Ontario population, Endangered` and the page names only the
  species, record only the species. Adding `population`, a scientific name, or a
  status the page does not print is filling in a template, and the answer is
  discarded for saying more than its quote.
- **List every item, not the clearest one.** Where a field can hold several
  things, a partial list is a wrong answer rather than a short one. Two readers
  who both read the page correctly and report different halves of the same list
  have both failed. Completeness here means more *entries*; it never means more
  words about one item, and a padded quote fails the mechanical check anyway.
- Answer every field in the specification. Omitting one is not the same as null.


Answer the fields and nothing else. The numbered conditions are read
separately by a different reader; do not record them here.

Reply with the single word `done` and nothing else. Your reply is not read:
everything about this run is derived from the file you wrote. Prose in a
reply is carried by the process that spawned you for the rest of its work,
so a report here costs more than it can be worth.

Read only the paths you are given. If something you need is missing, say so
in your reply rather than looking for it.
