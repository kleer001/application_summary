# Terms — Fisheries Act authorization extraction

Overlays the house list. Audience for documents here is a discipline lead or
project manager at an environmental consultancy, or an engineer executing the
work who was not part of the discussion that produced it.

## Domain terms

Words every dictionary holds and no outsider knows. The detector cannot guess
these; they are named here so it reports them.

- watercourse
- foreshore
- entrainment
- impingement
- aboiteau

## Decided - keep and gloss

The gloss to use at first use. Reported on every run as a reminder to check the
gloss is actually present.

- riprap: loose rock placed on a bank to stop it eroding
- HADD: harmful alteration, disruption or destruction of fish habitat
- PATH: the DFO file number carried on every authorization
- habitat bank: habitat restored in advance, drawn on later to offset a project
- cofferdam: a temporary watertight enclosure letting crews work on dry ground
- estuarine: where a river meets the sea and fresh water mixes with salt
- proponent: who holds the authorization
- offsetting: habitat work required to compensate for the harm
- authorization: the permit DFO issues allowing work that will harm fish habitat
- culvert: a pipe or box carrying a watercourse under a road or rail line
- OCR: the text layer a machine read off a scan, noisy and often wrong
- reader: an AI agent given one document and a list of questions
- pass: one sweep over the documents asking one kind of question
- wave: a batch of documents inside a pass
- pre-flight: a wave of one document, run to test the questions
- excerpt: one document's pages of text, sliced out of the source
- sandbox: a directory holding only what a reader is allowed to see
- holdout: labelled documents held back, scored once at the end
- anchor: the page range a value was read from
- canary: a document with a known-disputed value, used to detect leakage
- fleet mode: GitHub Copilot's way of running subagents in parallel from a task
  table
- harness: Microsoft's word for one of Copilot Studio's three runtimes

## Decided - replace

- zero-rated: charged at no cost
- content processing meter: the per-page charge for reading a document
- authenticated licensed user's identity: a person holding a paid licence, who
  set the work going
- extensibility contract: how it behaves, for anything built on it
- SDK: developer kit
- token ceiling: how much text it will accept
- utilise: use
- commence: start
- in order to: to
- ISO date: date recorded as YYYY-MM-DD

## Decided - fine as-is

- xlsx
- subagent
- filesystem
- lossy
- verifier
- API
- SQL
- DFO
- PDF
- HPAC
- HCAA
- HGLF
- HMAR
- HQUE
- HNFL
- riparian
- intertidal
- subtidal
- waterbody
- impoundment
- redacted
- conflated
- open-ended
- whitespace
- granularities
- part-pdfs
- jsonl
- segment
- manifest
- queue
- AI
- YYYY
- MM
- DD
- yyyy-mm-dd
- another's
- controlled-vocabulary
- prior-row
- adjudicator: a third reader that settles a disagreement against the scan
- arm: one version of a run, kept beside the others so they can be compared
- agent time: how long the AI spent working, as against how long the calendar ran
