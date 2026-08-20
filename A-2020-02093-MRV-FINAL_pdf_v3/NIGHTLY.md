# One night of reading

You are running one scheduled piece of a long extraction. Follow this exactly.
`RUN-PLAN.md` in the repository root says why it is shaped this way; you do not
need it to do the work.

Everything you need is in this repository. Do not look for the source release: it
is 340 MB and is not here. The documents have already been cut into per-document
excerpts under `staged/`, and that is all a reader ever sees.

## 1. Ask what is outstanding

From the repository root:

```
python3 A-2020-02093-MRV-FINAL_pdf_v3/nightly.py
```

**If it exits 3, stop.** The corpus is fully read. Do nothing else, commit nothing,
and say so in one line. This is the expected ending, not a failure — the schedule
keeps firing after the work is finished and each firing costs nothing.

Otherwise it prints one line per read, tab-separated:

```
stem <TAB> pass+reader <TAB> model <TAB> language <TAB> contract <TAB> slice <TAB> pdf <TAB> out
```

Take that list as given. Do not re-derive it, filter it, or decide some of it looks
unnecessary — a read appears there only because its output file does not exist.

## 2. Spawn one reader per line

For each line, spawn a `page-reader` subagent **on the model named in column 3** —
that column is the language routing already decided, and overriding it costs
accuracy on French documents.

Launch them together so they run concurrently, and hand each one exactly this:

```
Read one staged authorization document and record what it says.

Your instructions are the contract file. Read it first and follow it exactly.

- contract: <column 5>
- field specification: A-2020-02093-MRV-FINAL_pdf_v3/fields.json
- text excerpt: <column 6>
- PDF of the same pages: <column 7>
- output path: <column 8>

document_id is <column 1>. Write only the output path above. If you cannot write
it, say so plainly and do not write anywhere else.
```

Readers reply with the single word `done`. That is correct and deliberate. Do not
ask them for more, do not summarise what they found, and do not read their output
files to check — anything you take back from a reader stays in your context and is
re-read on every turn you take afterwards.

If a reader reports it could not write its output path, record that and continue.
A missing file is simply outstanding again on the next run.

## 3. Stamp what landed

```
python3 A-2020-02093-MRV-FINAL_pdf_v3/stamp.py A-2020-02093-MRV-FINAL_pdf_v3
```

This records on each new file which contract version produced it. Without it, a
later contract change cannot be told from an earlier one and the whole corpus has
to be re-read to be sure.

## 4. Confirm from the files, not from memory

```
python3 A-2020-02093-MRV-FINAL_pdf_v3/nightly.py --status
```

The count it prints is the truth about this run. An agent's own account of what it
did is not evidence — readers have been observed reporting success while writing
nowhere.

## 5. Commit and push

The sandbox is discarded when you finish. Work that is not pushed is lost, and a
read cannot be reproduced — re-running produces a different answer, not the same
one again.

```
git add A-2020-02093-MRV-FINAL_pdf_v3/run2/out
git commit -m "read <n> documents"
git push
```

## 6. Report

One short paragraph: how many reads landed, how many remain, and anything that
failed. Do not restate what the documents said.

## What not to do

- Do not edit the contracts, the field specification, or the work order.
- Do not run `build.py`, `qc.py` or `score.py`. They need dependencies that are not
  installed here and they are not part of a reading night.
- Do not open the prior summary workbook. It is a test set, and nothing but
  `score.py` may read it.
- Do not raise `documents_per_night` in `nightly.json` on your own initiative.
