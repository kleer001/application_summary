"""Quality control on a built workbook, and quality assurance on the run.

Quality control asks a question about the artifact: is every filled cell in this
workbook one that can be checked against the page it cites? It re-derives the
answer from the reader output rather than trusting the build, so a bug in
build.py cannot sign its own work off.

Quality assurance asks a question about the process: was this workbook produced
the way the specification says it must be? Two readers who never saw each
other's answers, a specification that was never shown the holdout, an
adjudication whose every non-agreement is recorded.

A workbook can pass control and fail assurance, and the reverse. Both are
reported, and neither is a percentage: a checkable cell either is or is not.
"""
import hashlib, json, os, sys
from collections import Counter, defaultdict

import openpyxl

from adjudicate import adjudicate
from build import INFERRED, PRIOR, VOCABULARIES
from norm import on_page
from verify import check_conditions, load_pages, verdicts_for

HERE = os.path.dirname(os.path.abspath(__file__))


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:12]


def control(sandbox, xlsx):
    """Every filled cell, back to a verified entry or to a stated derivation."""
    wb = openpyxl.load_workbook(xlsx, data_only=True)
    orders = json.load(open(f"{sandbox}/wave.json"))
    have = Counter(f.split(".")[0] for f in os.listdir(f"{sandbox}/out"))
    orders = [o for o in orders if have.get(o["stem"], 0) == 4]
    by_stem = {o["stem"]: o for o in orders}

    findings, checked = [], Counter()
    rejected, rejected_conditions = {}, set()

    # 1. every reader answer that reached a cell verified against its own page
    for stem, o in by_stem.items():
        for tag in ("a1", "a2"):
            doc = json.load(open(f"{sandbox}/out/{stem}.{tag}.json"))
            for name, verdict in verdicts_for(doc, o["slice"],
                                              o["first_page"], o["last_page"]).items():
                checked[f"field:{verdict}"] += 1
                if verdict in ("REJECT", "MALFORMED"):
                    rejected.setdefault((o["file_number"], name), []).append(
                        f"{stem} {tag}")
        for tag in ("b1", "b2"):
            doc = json.load(open(f"{sandbox}/out/{stem}.{tag}.json"))
            for num, verdict, _ in check_conditions(doc, o["slice"]):
                checked[f"condition:{verdict}"] += 1
                if verdict == "REJECT":
                    rejected_conditions.add((o["file_number"], str(num)))

    # 2. no cell in the summary carries an unadjudicated conflict
    conflicts = set()
    for stem, o in by_stem.items():
        A = json.load(open(f"{sandbox}/out/{stem}.a1.json"))["fields"]
        B = json.load(open(f"{sandbox}/out/{stem}.a2.json"))["fields"]
        for k in set(A) | set(B):
            ea = [e for e in (A.get(k) or {}).get("entries") or [] if e.get("value") not in (None, "")]
            eb = [e for e in (B.get(k) or {}).get("entries") or [] if e.get("value") not in (None, "")]
            if ea or eb:
                entries, verdict, _ = adjudicate(ea, eb)
                if verdict == "conflict":
                    conflicts.add((o["file_number"], k))
                    if entries:
                        findings.append(("a conflict resolved itself into a cell",
                                         f"{stem} {k}"))

    # 3. page citations lie inside the release, and inside the row's own range
    ws = wb["Authorization_Summary"]
    hdr = [c.value for c in ws[1]]
    ix = {h: i for i, h in enumerate(hdr)}
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    for r in rows:
        start, end = r[ix["Page_Start"]], r[ix["Page_End"]]
        anchor = str(r[ix["Source_Reference_ID"]] or "")
        if not (isinstance(start, int) and isinstance(end, int) and 1 <= start <= end):
            findings.append(("row has no usable page range", str(r[ix["DFO_File_or_PATH"]])))
        elif anchor.startswith("pp. "):
            lo, hi = (int(x) for x in anchor[4:].split("-"))
            if lo < start or hi > end:
                findings.append(("page anchor outside the row's own pages", anchor))
        checked["rows"] += 1

    # 4. derived cells say so, quoted cells do not
    # Reasoned columns: the derivations in the prior layout, and every pass D
    # vocabulary. Both are labels rather than quotes, and both must say so.
    derived = ({name for name, src in PRIOR if src.startswith("@")}
               | {v.replace("_", " ").title().replace(" ", "_") for v in VOCABULARIES})
    for r in rows:
        for name, cell in zip(hdr, r):
            if cell in (None, ""):
                continue
            marked = str(cell).rstrip().endswith(INFERRED.strip())
            if marked and name not in derived:
                findings.append(("a quoted cell is marked as reasoned", name))
            checked["cells"] += 1

    # 5. a value that failed verification never reached a cell
    fieldcol = {src: name for name, src in PRIOR if not src.startswith(("@", "-"))}
    for r in rows:
        fn = r[ix["DFO_File_or_PATH"]]
        for src, col in fieldcol.items():
            if (fn, src) in rejected and r[ix[col]] not in (None, ""):
                findings.append(("a cell holds a value that failed verification",
                                 f"{fn} {col}"))
    # Check the text the workbook actually carries, not the readers' drafts of it:
    # pass C may have replaced a condition whose reader copy the OCR defeated.
    # Keyed by document, not by file number: a merged row spans several
    # documents and each has its own page offset.
    ranges = {o["doc_id"]: o for o in orders}
    for c in wb["Conditions"].iter_rows(min_row=2, values_only=True):
        fn, doc_id, num, text, page, src = c[0], c[1], str(c[4]), c[8], c[9], c[10]
        o = ranges.get(doc_id)
        if not o or not text or not isinstance(page, int):
            continue
        folded = load_pages(o["slice"])
        rel = page - o["first_page"] + 1
        spread_f = folded.get(rel, ("", set()))[0] + folded.get(rel + 1, ("", set()))[0]
        spread_t = folded.get(rel, ("", set()))[1] | folded.get(rel + 1, ("", set()))[1]
        checked["conditions in the sheet"] += 1
        if on_page(text, spread_f, spread_t):
            continue
        if src == "image":
            checked["conditions read off the scan"] += 1     # not in the text layer by design
            continue
        findings.append(("a condition's text is not on the page the sheet cites",
                         f"{fn} {num} p{page}"))

    # 6. every condition belongs to a row that exists
    known = {r[ix["DFO_File_or_PATH"]] for r in rows}
    for c in wb["Conditions"].iter_rows(min_row=2, values_only=True):
        if c[0] not in known:
            findings.append(("condition belongs to no row in the summary", str(c[0])))
    return findings, checked, conflicts


def assurance(sandbox, xlsx, conflicts):
    """What the run did, stated so it can be disputed."""
    orders = json.load(open(f"{sandbox}/wave.json"))
    have = Counter(f.split(".")[0] for f in os.listdir(f"{sandbox}/out"))
    complete = {s for s, n in have.items() if n == 4}
    models = defaultdict(set)
    for o in orders:
        if o["stem"] in complete:
            models[o["pass"]].add(o["model"])

    wb = openpyxl.load_workbook(xlsx, data_only=True)
    return {
        "documents read": len(complete),
        "documents in the wave": len({o["stem"] for o in orders}),
        "readers per document": "2 for the fields, 2 for the conditions, independent",
        "model, pass A": ", ".join(sorted(models["a"])) or "-",
        "model, pass B": ", ".join(sorted(models["b"])) or "-",
        "field specification": sha(f"{HERE}/fields.json"),
        # The contract on disk is what the *next* read will follow, not what the
        # reads in this workbook followed. Report the versions the answers were
        # actually produced under, or a workbook built from a mixed corpus states
        # one clean hash and hides the mixture.
        "reader contract A": contracts_used(sandbox, "a"),
        "reader contract B": contracts_used(sandbox, "b"),
        "tuning and holdout split": sha(f"{HERE}/split.json"),
        "prior summary read during the build": "no",
        "rows in the workbook": wb["Authorization_Summary"].max_row - 1,
        "numbered conditions": wb["Conditions"].max_row - 1,
    }


def contracts_used(sandbox, pass_name):
    """The contract versions the answers in this sandbox were read under.

    Counted from the stamps on the reader files rather than from the contract
    file, so a corpus read across several versions reports as several versions.
    """
    seen = Counter()
    for name in sorted(os.listdir(f"{sandbox}/out")):
        if name.endswith(".json") and name.rsplit(".", 2)[1][0] == pass_name:
            seen[json.load(open(f"{sandbox}/out/{name}")).get("contract", "unstamped")] += 1
    if not seen:
        return "-"
    now = sha(f"{HERE}/contract_{pass_name}.md")
    return ", ".join(f"{h} ({n}{'' if h == now else ', not the version now on disk'})"
                     for h, n in seen.most_common())


def workload(xlsx):
    """What the queue actually asks of a person, read off the sheet itself.

    Reported here, from the artifact, because a summary written by hand drifts
    toward whatever the writer last remembered. A queue that files advisories as
    work overstates what is owed, and an overstated queue gets ignored.
    """
    wb = openpyxl.load_workbook(xlsx, data_only=True)
    decisions = list(wb["Review_Queue"].iter_rows(min_row=2, values_only=True))
    notes = list(wb["Provenance"].iter_rows(min_row=2, values_only=True))
    kinds = Counter()
    for r in decisions:
        why = str(r[3])
        kinds["a number one reader read as a heading" if "as a heading introducing" in why
              else "a condition whose text is not on its cited page" if "does not appear" in why
              else "a field conflict pass C has not settled" if "conflict" in why or "different answers" in why
              else "a field neither reader verified" if "neither reader" in why
              else "pass C could not settle it" if "could not settle" in why
              else "other"] += 1
    return len(decisions), len(notes), kinds


if __name__ == "__main__":
    sandbox, xlsx = sys.argv[1], sys.argv[2]
    findings, checked, conflicts = control(sandbox, xlsx)

    print("QUALITY CONTROL — is every filled cell checkable?\n")
    for k in sorted(checked):
        print(f"    {checked[k]:6}  {k}")
    print()
    if findings:
        counts = Counter(f for f, _ in findings)
        for what, n in counts.most_common():
            print(f"    FAIL  {n:4}  {what}")
            for w, where in [f for f in findings if f[0] == what][:3]:
                print(f"                  {where}")
    else:
        print("    PASS  no cell in this workbook fails its own check")

    print("\n\nQUALITY ASSURANCE — was it produced the way the plan requires?\n")
    for k, v in assurance(sandbox, xlsx, conflicts).items():
        print(f"    {k:38} {v}")

    decisions, notes, kinds = workload(xlsx)
    print(f"\n\nWHAT THE QUEUE ASKS OF A PERSON\n")
    print(f"    {decisions:6}  decisions owed")
    for k, n in kinds.most_common():
        print(f"    {n:6}    {k}")
    print(f"    {notes:6}  notes, needing no decision")
    print()
    sys.exit(1 if findings else 0)
