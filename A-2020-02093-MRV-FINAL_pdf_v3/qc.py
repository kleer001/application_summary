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
import hashlib, json, os, re, sys
from collections import Counter, defaultdict

import openpyxl

from adjudicate import adjudicate
from build import INFERRED, PRIOR, VOCABULARIES, adjudications
from norm import norm, on_page
from ids import corrected, file_no_of, stem_of
from paths import complete_stems
from stamp import current as contracts_in_force, pass_of, sha, stamp_of
from verify import (FAILED, VERIFIED, check_conditions, check_field, load_pages,
                    on_cited_page, verdicts_for)

HERE = os.path.dirname(os.path.abspath(__file__))


def control(sandbox, xlsx):
    """Every filled cell, back to a verified entry or to a stated derivation."""
    wb = openpyxl.load_workbook(xlsx, data_only=True)
    orders = json.load(open(f"{sandbox}/wave.json"))
    complete = complete_stems(sandbox)
    orders = [o for o in orders if o["stem"] in complete]
    by_stem = {o["stem"]: o for o in orders}

    findings, checked = [], Counter()
    rejected, rejected_conditions, verified = {}, set(), set()
    filed = defaultdict(set)            # stem -> the authorizations it files under

    # 1. every reader answer that reached a cell verified against its own page
    for stem, o in by_stem.items():
        for tag in ("a1", "a2"):
            doc = json.load(open(f"{sandbox}/out/{stem}.{tag}.json"))
            verdicts = verdicts_for(doc, o["slice"], o["first_page"], o["last_page"])
            for name, verdict in verdicts.items():
                checked[f"field:{verdict}"] += 1
                if verdict in FAILED:
                    rejected.setdefault((corrected(o["stem"], o["file_number"]), name), []).append(
                        f"{stem} {tag}")
                elif verdict in VERIFIED:
                    verified.add((corrected(o["stem"], o["file_number"]), name))
        for tag in ("b1", "b2"):
            doc = json.load(open(f"{sandbox}/out/{stem}.{tag}.json"))
            for num, verdict, _ in check_conditions(doc, o["slice"]):
                checked[f"condition:{verdict}"] += 1
                if verdict == "REJECT":
                    rejected_conditions.add((corrected(o["stem"], o["file_number"]), str(num)))

        # An adjudicated answer is a verified answer too, where it verifies. Pass
        # C reads the pages a reader read and may find what the reader could not,
        # which is the whole point of the briefs that carry a question rather
        # than two candidates. Re-checked here rather than taken from the build:
        # this file exists to test that workbook, not to agree with it.
        for name, a in adjudications(sandbox, o["doc_id"]).items():
            if not a.get("entries") or name.startswith(("condition ", "heading ")):
                continue
            verdict = check_field(name, {"entries": a["entries"]}, load_pages(o["slice"]),
                                  o["last_page"] - o["first_page"] + 1)[1]
            checked[f"adjudicated:{verdict}"] += 1
            if verdict in VERIFIED:
                verified.add((corrected(o["stem"], o["file_number"]), name))

    # 2. no cell in the summary carries an unadjudicated conflict
    for stem, o in by_stem.items():
        A = json.load(open(f"{sandbox}/out/{stem}.a1.json"))["fields"]
        B = json.load(open(f"{sandbox}/out/{stem}.a2.json"))["fields"]
        for k in set(A) | set(B):
            ea = [e for e in (A.get(k) or {}).get("entries") or [] if e.get("value") not in (None, "")]
            eb = [e for e in (B.get(k) or {}).get("entries") or [] if e.get("value") not in (None, "")]
            if ea or eb:
                entries, verdict, _ = adjudicate(ea, eb)
                if verdict == "conflict" and entries:
                    findings.append(("a conflict resolved itself into a cell",
                                     f"{stem} {k}"))
                # The adjudicated entries are what the build splits rows on, so
                # they are what check 7 has to be asked about. Taken here rather
                # than from either reader alone: the union of the two would demand
                # a row the build was never given a reason to make.
                filed[stem] |= {e["authorization"] for e in entries
                                if e.get("authorization")}

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

    # The extended fields moved to their own sheet, and the count of checkable
    # cells has to move with them. Nothing there is derived except the identifier,
    # which carries the marker when the build had to infer it.
    es = wb["Extended_Fields"]
    ehdr = [c.value for c in es[1]]
    erows = list(es.iter_rows(min_row=2, values_only=True))
    for r in erows:
        for name, cell in zip(ehdr, r):
            if cell in (None, ""):
                continue
            marked = str(cell).rstrip().endswith(INFERRED.strip())
            if marked and name != "DFO_File_or_PATH":
                findings.append(("a quoted cell is marked as reasoned", name))
            checked["cells"] += 1

    # 5. a value that failed verification never reached a cell
    fieldcol = {src: name for name, src in PRIOR if not src.startswith(("@", "-"))}
    # The identifier column is derived so that a row is never nameless, but where
    # it holds the quoted field it is still that field and still has to answer
    # for it. Marking it derived must not buy the one column the whole row hangs
    # on an exemption from the check below; only the inferred fallback is exempt,
    # and it says so in the cell.
    fieldcol.setdefault("file_number", "DFO_File_or_PATH")
    for r in rows:
        fn = r[ix["DFO_File_or_PATH"]]
        # Verdicts are recorded against the document's own key. A row split out
        # of a letter granting several authorizations is filed under one of the
        # numbers the letter grants, which is not that key, so asking with the
        # row's own key would quietly test nothing for two rows in three.
        keys = {corrected(stem_of(d), file_no_of(d))
                for d in str(r[ix["Documents"]] or "").split("; ") if d}
        for src, col in fieldcol.items():
            # One reader failing is not a failed cell. The build discards that
            # reader and keeps the other, so the cell holds an answer that did
            # verify. What this looks for is a filled cell with no verified
            # answer behind it at all.
            value = r[ix[col]]
            if str(value).rstrip().endswith(INFERRED.strip()):
                continue                      # reasoned, and says so
            if (any((k, src) in rejected for k in keys)
                    and not any((k, src) in verified for k in keys)
                    and value not in (None, "")):
                findings.append(("a cell holds a value that failed verification",
                                 f"{fn} {col}"))
    # The same question of the sheet next door. Its column names are the field
    # names, so no mapping is needed -- and these were never covered while they
    # sat in the summary, because that check only ever walked the prior layout.
    efields = [h for h in ehdr if h not in ("DFO_File_or_PATH", "Documents")]
    for r in erows:
        d = dict(zip(ehdr, r))
        keys = {corrected(stem_of(x), file_no_of(x))
                for x in str(d.get("Documents") or "").split("; ") if x}
        for src in efields:
            value = d.get(src)
            if value in (None, "") or str(value).rstrip().endswith(INFERRED.strip()):
                continue
            if (any((k, src) in rejected for k in keys)
                    and not any((k, src) in verified for k in keys)):
                findings.append(("a cell holds a value that failed verification",
                                 f"{d.get('DFO_File_or_PATH')} {src}"))

    # Check the text the workbook actually carries, not the readers' drafts of it:
    # pass C may have replaced a condition whose reader copy the OCR defeated.
    # Keyed by document, not by file number: a merged row spans several
    # documents and each has its own page offset.
    ranges = {o["doc_id"]: o for o in orders}
    cs = wb["Conditions"]
    cix = {c.value: i for i, c in enumerate(cs[1])}
    for c in cs.iter_rows(min_row=2, values_only=True):
        fn, doc_id = c[cix["File_Number"]], c[cix["Document"]]
        num, text = str(c[cix["Number"]]), c[cix["Text"]]
        page, src = c[cix["Page"]], c[cix["Source"]]
        o = ranges.get(doc_id)
        if not o or not text or not isinstance(page, int):
            continue
        folded = load_pages(o["slice"])
        rel = page - o["first_page"] + 1
        checked["conditions in the sheet"] += 1
        if on_cited_page(text, folded, rel):
            continue
        if src == "image":
            checked["conditions read off the scan"] += 1     # not in the text layer by design
            continue
        findings.append(("a condition's text is not on the page the sheet cites",
                         f"{fn} {num} p{page}"))

    # 6. every condition belongs to a row that exists
    # An identifier the build had to infer carries the project's inferred
    # marker; the Conditions sheet keys on the bare file number. Compare the
    # identity, not the marker, or a row that names itself still orphans its
    # conditions.
    known = {str(r[ix["DFO_File_or_PATH"]]).removesuffix(INFERRED)
             for r in rows if r[ix["DFO_File_or_PATH"]]}
    for c in cs.iter_rows(min_row=2, values_only=True):
        fn = c[cix["File_Number"]]
        if fn not in known:
            findings.append(("condition belongs to no row in the summary", str(fn)))

    # 7. every authorization a letter files figures under has a row of its own
    #
    # One row cannot be the record of three authorizations: its area cells would
    # hold figures from three separate decisions with nothing to say which is
    # which. Asked of the attribution rather than of how many numbers the letter
    # prints, because that is what makes the rows separable — a letter naming a
    # second number it does not sort anything under grants one authorization and
    # belongs in one row. Read off the readers, because the sheet cannot report a
    # row it never grew.
    folded = {norm(k) for k in known}
    for stem, numbers in filed.items():
        if len(numbers) < 2:
            continue
        checked["letters filing figures under several authorizations"] += 1
        for n in sorted(numbers):
            if norm(n) not in folded:
                findings.append(("an authorization the letter files under has no row",
                                 f"{stem} {n}"))
    return findings, checked


def assurance(sandbox, xlsx):
    """What the run did, stated so it can be disputed."""
    orders = json.load(open(f"{sandbox}/wave.json"))
    complete = complete_stems(sandbox)
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
        if name.endswith(".json") and pass_of(name) == pass_name:
            seen[stamp_of(f"{sandbox}/out/{name}")] += 1
    if not seen:
        return "-"
    now = contracts_in_force()[pass_name]
    return ", ".join(f"{h} ({n}{'' if h == now else ', not the version now on disk'})"
                     for h, n in seen.most_common())


# What each reason still owes, and to whom. Keyed on the code the build stamps
# on the entry, not on the sentence beside it — the sentence is free to be
# reworded. Every code here is work pass C takes: an adjudicator is given the
# scan as well as the two answers, which is what lets it settle "what does the
# page say" and not only "which of these two is right".
WORKLOAD = {
    "conflict": "a field conflict pass C has not settled",
    "heading_dispute": "a number one reader read as a heading",
    "neither_verified": "a field neither reader verified",
    "condition_off_page": "a condition whose text is not on its cited page",
    "passc_unsettled": "pass C could not settle it",
    "passc_failed_check": "a pass C answer that failed its own check",
    "no_file": "a reader that wrote no file",
}


# A condition pointing at a number the document does not carry. Both readers can
# read such a line correctly and agree about it, so no amount of agreement finds
# it: the defect is the document's, and it is visible only by following the
# reference to its target. Observed in this release: 4.4.1.3 of 19-HCAA-00130
# requires targets "described in conditions 4.3.5 and 4.3.6" where section 4.3
# ends at 4.3.5.
#
# Only references of two components or more are followed. "Condition 5" names a
# whole section, which is a heading and not necessarily a recorded number, and
# checking those reports the document's own structure as a fault.
REFERENCE = re.compile(
    r"\b(?:conditions?|sections?|articles?|paragraphes?)\s+"
    r"((?:\d+\.){1,4}\d+)((?:\s*(?:,|and|et|or|ou)\s*(?:\d+\.){1,4}\d+)*)",
    re.I)
EXTERNAL = re.compile(r"^\s*(of|de|du)\s+(the|l|la|le)?", re.I)


# A number alone on its line counts: "4.4." with its text on the line below is
# how the scanner renders a heading whose wording wrapped.
NUMBERED_LINE = re.compile(r"^\s*((?:\d+\.){1,4}\d*)\.?(?:\s|$)")


def numbers_printed(slice_path):
    """Every number the document itself prints at the start of a line.

    Taken from the page text rather than from what the readers kept, because a
    parent ruled a heading is dropped from the workbook while remaining a number
    the document prints. Checking references against the kept set would report
    this pipeline's own decisions as the document's errors.
    """
    if not os.path.exists(slice_path):
        return set()
    out = set()
    for line in open(slice_path, encoding="utf-8", errors="replace"):
        m = NUMBERED_LINE.match(line)
        if m:
            out.add(m.group(1).rstrip("."))
    # A parent every one of whose children is printed is itself a number the
    # document carries, whether or not its own line survived the scan. Without
    # this, a reference to "4.2" is reported as dangling on a document that
    # prints 4.2.1 through 4.2.5.
    for n in list(out):
        parts = n.split(".")
        for i in range(1, len(parts)):
            out.add(".".join(parts[:i]))
    return out


def cross_references(sandbox):
    """Numbers a document's own conditions cite that the document never prints.

    Both readers can read such a line correctly and agree about it, so no amount
    of agreement finds it: the defect is the document's, and it is visible only
    by following the reference to its target.
    """
    orders = {o["stem"]: o for o in json.load(open(f"{sandbox}/wave.json"))}
    dangling = set()
    for stem in sorted(complete_stems(sandbox)):
        order = orders.get(stem)
        if not order:
            continue
        present = numbers_printed(order["slice"])
        for tag in ("b1", "b2"):
            path = f"{sandbox}/out/{stem}.{tag}.json"
            if not os.path.exists(path):
                continue
            for c in json.load(open(path)).get("conditions") or []:
                if c.get("number"):
                    present.add(str(c["number"]).rstrip("."))
        for tag in ("b1", "b2"):
            path = f"{sandbox}/out/{stem}.{tag}.json"
            if not os.path.exists(path):
                continue
            for c in json.load(open(path)).get("conditions") or []:
                text = c.get("text") or ""
                for m in REFERENCE.finditer(text):
                    if EXTERNAL.match(text[m.end():m.end() + 12]):
                        continue              # a section of some other document
                    cited = [m.group(1)] + re.findall(r"(?:\d+\.){1,4}\d+", m.group(2) or "")
                    for target in cited:
                        if target.rstrip(".") not in present:
                            dangling.add((stem, str(c.get("number")), target))
    return sorted(dangling)


def workload(xlsx):
    """What the queue still has to settle, read off the sheet itself.

    Reported here, from the artifact, because a summary written by hand drifts
    toward whatever the writer last remembered. A queue that files advisories as
    work overstates what is owed, and an overstated queue gets ignored.

    These are adjudications outstanding, not questions for a person. What makes
    that safe is not that an adjudicator is never wrong: it is that every value
    it writes carries the pages it came from, and the check above fails the
    workbook if a quote is not on the pages its own row cites.
    """
    wb = openpyxl.load_workbook(xlsx, data_only=True)
    decisions = list(wb["Review_Queue"].iter_rows(min_row=2, values_only=True))
    notes = list(wb["Provenance"].iter_rows(min_row=2, values_only=True))
    kinds = Counter()
    for r in decisions:
        kinds[WORKLOAD.get(r[4], "other")] += 1
    return len(decisions), len(notes), kinds


if __name__ == "__main__":
    sandbox, xlsx = sys.argv[1], sys.argv[2]
    findings, checked = control(sandbox, xlsx)

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

    # Reported, never fatal. The workbook is not wrong because the document is;
    # what would be wrong is copying the reference out without saying so.
    dangling = cross_references(sandbox)
    print("\n\nWHAT THE DOCUMENTS THEMSELVES GET WRONG\n")
    if dangling:
        for stem, number, target in dangling:
            print(f"    {stem} condition {number} cites {target}, which the "
                  f"document never prints")
    else:
        print("    none — every condition cross-reference resolves")

    print("\n\nQUALITY ASSURANCE — was it produced the way the plan requires?\n")
    for k, v in assurance(sandbox, xlsx).items():
        print(f"    {k:38} {v}")

    decisions, notes, kinds = workload(xlsx)
    print(f"\n\nWHAT THE QUEUE STILL HAS TO SETTLE\n")
    print(f"    {decisions:6}  adjudications outstanding")
    for k, n in kinds.most_common():
        print(f"    {n:6}    {k}")
    print(f"    {notes:6}  notes, needing no decision")
    print()
    sys.exit(1 if findings else 0)
