# One night of reading

You are running one scheduled piece of a long extraction. Follow this exactly.
`RUN-PLAN.md` in the repository root says why it is shaped this way; you do not
need it to do the work.

Everything you need is in this repository. Do not look for the source release: it
is 340 MB and is not here. The documents have already been cut into per-document
excerpts under `staged/`, and that is all a reader ever sees.

## 0. Make the scans readable

```
pdftoppm -v >/dev/null 2>&1 || (apt-get update -qq && apt-get install -y -qq poppler-utils)
pdftoppm -v
```

**If this fails, stop and report it. Do not read anything.** Without `poppler-utils`
a reader cannot render the page images, and the sandbox is otherwise silent about
it: the PDF read returns an error the reader is free to shrug off, and it will go on
to answer from the text layer alone while still recording that it corroborated its
answers against the scan. Measured on a probe run, every one of 35 entries claimed
`source: "both"` on a document whose scan had never been rendered.

The text layer is a lossy machine transcription. Readers use the scan to recover
`m²` from `m°`, `1er` from `1°`, and section numbers the text layer drops entirely.
A night that runs without it produces answers that are worse and that misreport
where they came from.

## 1. Ask what is outstanding

From the repository root:

```
python3 A-2020-02093-MRV-FINAL_pdf_v3/nightly.py --retire
```

A read is outstanding when its output is missing, and equally when its output was
produced under a contract that has since changed in a way that can alter the
answer. `--retire` moves such an answer into `superseded/` before the re-read, so
the new one has somewhere to land and the old one survives as evidence of what
the page was read to say under the earlier contract. Without the flag the same
list is printed and nothing is moved, which is how to look without acting.

**If it exits 3, there is nothing left to read.** Skip steps 2 and 3 and go
straight to step 4: a corpus that has been read through is not a corpus whose
disagreements are settled, and adjudication outlasts reading by some nights.

The ending is when step 1 and step 4 *both* have nothing outstanding. On such a
night, commit nothing and say so in one line. That is the expected ending and not
a failure — the schedule keeps firing after the work is done and a firing that
does nothing costs nothing.

Otherwise it prints one line per read, tab-separated:

```
stem <TAB> pass+reader <TAB> model <TAB> language <TAB> contract <TAB> slice <TAB> pdf <TAB> out
```

Take that list as given. Do not re-derive it, filter it, or decide some of it looks
unnecessary — a read appears there only because its output file does not exist.

## 2. Spawn one reader per line, a batch at a time

For each line, spawn a `page-reader` subagent **on the model named in column 3** —
that column is the language routing already decided, and overriding it costs
accuracy on French documents.

The list is divided into batches by `# batch N of M` lines. **Launch every reader
in a batch together, wait until all of them have replied, then start the next
batch.** Concurrency is capped and the excess is rejected rather than queued, so
a batch dispatched on top of a running one loses reads silently — they simply
never write a file, and the only sign is a smaller count in step 5. Most nights
are a single batch and this costs nothing.

Hand each reader exactly this:

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

A batch is finished when every reader in it has replied. Do not start the next on
a timer or because most are done.

If a reader reports it could not write its output path, record that and continue.
A missing file is simply outstanding again on the next run.

Output files appear one at a time while readers are still running, so a hook or a
check may report untracked files mid-run. That is expected. Committing is step 5 and
happens once, after every reader has finished and `stamp.py` has run.

## 3. Stamp what landed

```
python3 A-2020-02093-MRV-FINAL_pdf_v3/stamp.py A-2020-02093-MRV-FINAL_pdf_v3/run2
```

This records on each new file which contract version produced it. Without it, a
later contract change cannot be told from an earlier one and the whole corpus has
to be re-read to be sure.

## 4. Settle what the readers disagreed about

```
python3 A-2020-02093-MRV-FINAL_pdf_v3/conflicts.py A-2020-02093-MRV-FINAL_pdf_v3/run2
python3 A-2020-02093-MRV-FINAL_pdf_v3/passc.py A-2020-02093-MRV-FINAL_pdf_v3/run2
```

Both exit 3 when they have nothing outstanding. If either does, there is nothing
to adjudicate tonight: go to step 5 if reads landed, or finish as described in
step 1 if none did. Neither builds the workbook and neither needs anything but the
standard library.

`passc.py` prints one line per adjudication, capped by `adjudications_per_night`,
tab-separated:

```
stem <TAB> field <TAB> model <TAB> brief <TAB> fields <TAB> slice <TAB> pdf <TAB> out
```

Spawn one `page-reader` subagent per line, on the model in column 3, and hand it
exactly this:

```
Adjudicate one disagreement between two readers of an authorization document.

Your instructions are the contract file. Read it first and follow it exactly.

- contract: A-2020-02093-MRV-FINAL_pdf_v3/contract_c.md
- the disagreement, with both readers' answers and what each cited: <column 4>
- field specification: <column 5>
- text excerpt: <column 6>
- PDF of the same pages: <column 7>
- output path: <column 8>

The document id and the field are in the brief. Pages are numbered from 1, as in
the excerpt and the PDF. Write only the output path above. If you cannot write
it, say so plainly and do not write anywhere else.
```

Adjudicators reply `done`, for the same reason readers do. An adjudicated answer
is checked against the page it cites exactly as a reader's is, when the workbook
is next built; one that cannot be found there is discarded and the conflict
stands. So there is nothing to review here, and nothing to take back into your
context.

A conflict is listed only while no ruling for it exists, and only while both of
its reads are on a contract still in force. Documents waiting to be re-read are
held back rather than settled against answers that are about to change.

## 5. Confirm from the files, not from memory

```
python3 A-2020-02093-MRV-FINAL_pdf_v3/nightly.py --status
```

The count it prints is the truth about this run. An agent's own account of what it
did is not evidence — readers have been observed reporting success while writing
nowhere.

## 6. Commit and push

The sandbox is discarded when you finish. Work that is not pushed is lost, and a
read cannot be reproduced — re-running produces a different answer, not the same
one again.

The sandbox comes up on a detached HEAD, and its `main` and `origin/main` refs are
stale — they point at an older commit than the checkout itself. Do not check out a
branch, do not fast-forward one, and do not trust `git log main`. Push the commit
you just made straight to the remote branch:

```
git add A-2020-02093-MRV-FINAL_pdf_v3/run2
git commit -m "read <n> documents, settled <m> conflicts"
git push origin HEAD:main
```

If that push is rejected as non-fast-forward, the checkout was behind the remote.
Report it and stop; do not merge, rebase or force.

## 7. Report

One short paragraph: how many reads landed, how many adjudications were settled,
how many remain, and anything that failed. Do not restate what the documents
said and do not report what any adjudicator decided.

## What not to do

- Do not edit the contracts, the field specification, or the work order.
- Do not run `build.py`, `qc.py` or `score.py`. They need dependencies that are not
  installed here and they are not part of a night's work. `conflicts.py` imports
  `build.py` and that is fine: it uses the half that finds disagreements, not the
  half that writes a spreadsheet.
- Do not open the prior summary workbook. It is a test set, and nothing but
  `score.py` may read it.
- Do not raise `documents_per_night` or `adjudications_per_night` in `nightly.json`
  on your own initiative.
