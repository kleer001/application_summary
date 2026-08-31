# v3 — status

The plan is `../PLAN-v3.md`. The pipeline is built and has been run over part of
the release; `qc.py` is the gate that says whether a workbook may be trusted.

## Running it

```
wave.py   <sandbox> --split tune     stage documents, write the work order
  readers                            two per document per pass, model named in the order
  adjudicators                       one per conflict the mechanical rules could not settle
passd.py  <sandbox> <out.xlsx>       vocabularies and rows for the labellers
  labellers                          one per vocabulary, each given every row
build.py  <sandbox> <out.xlsx>       combine, merge, write the workbook
qc.py     <sandbox> <out.xlsx>       control on the artifact, assurance on the run
status.py <sandbox>                  what the wave still owes
```

`wave.json` is the work order: one line per read, naming the document, the pass,
the contract, the model and where the answer goes. Anything that can spawn an
agent executes it without further instruction.

## The four rungs of disagreement

Two readers read every document. What they disagree about is sorted before
anybody is asked to look at it.

| | settled by |
|---|---|
| the same answer | agreement |
| the same passage quoted to different lengths | `adjudicate.py` — texture |
| one reader listing fewer items than the other | `adjudicate.py` — lapse |
| genuinely different answers | pass C, an adjudicator reading the cited pages |
| the pages do not settle it | a person |

An adjudicator is bound by the reader contract it arbitrates: its answers carry
quotes and pages, are verified identically, and stay in the document's language.
Over 38 conflicts on the first eighteen documents it returned `unresolved` zero
times, and twice found the right answer in neither reader's column.

## `run/`

The output of the partial run so far — reader files, adjudications, labels and the
workbook built from them. Kept in the repo because a re-run would replace it
rather than reproduce it, and because it is the evidence behind every figure
quoted about this run. See `run/README.md`.

`preflight/` holds the earlier two-reader trials that shaped the specification,
under contracts that have since changed.

## Do not regenerate `split.json`

46 tuning and 46 holdout file numbers, of the 92 appearing in both the documents
and the prior summary. Regenerating it, even with identical code, destroys the
claim that the specification was never tuned against the holdout.

## Sandboxes go in `tmp/`, not `/tmp`

Stage into `<repo>/tmp/<run>`. The system `/tmp` is cleared without warning, and
reader output is not reproducible — re-running produces different files, not the
same ones again. `tmp/` is gitignored; promote anything that turns out to be
evidence into a real directory, as `run/` was.

## The sandbox path must be short

Readers are handed absolute paths and retype them. One turned `application-summary`
into `application_summary` and correctly reported the file missing rather than
going looking. Keep the run directory shallow — `tmp/w1`, not a nested path.

## What is known-incomplete

- The tuning half is partly read; the holdout is untouched.
- Pass D labels only the rows built at the time it ran. A row read afterwards
  carries no label until the pass is run again, and the pass replaces every
  label rather than adding to them.
- `Supporting_Documents` is a finding aid, not extraction. The segmenter cannot
  reach those documents — it looks for an "issued to" block they do not have — so
  their titles and page ranges are recorded by hand in `supporting_documents.json`
  and copied to the sheet unchanged. Each title is quoted from the page cited
  beside it; nothing else on the sheet is claimed.
- The earliest documents were read under older versions of the contracts, so
  their conflict rate is not a measurement of the current ones.
