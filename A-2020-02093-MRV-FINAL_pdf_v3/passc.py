"""The adjudications outstanding, and the brief each one needs.

conflicts.py says which fields two readers disagreed about. It cannot say what
they disagreed about: by the time a conflict is filed, the answers have been
folded to compare them and the pages have been made absolute to place them in
the workbook. contract_c.md promises an adjudicator both answers with the quotes
and pages each reader cited, which means going back to what the readers wrote.

So this reads the raw reader output, writes one brief per conflict, and prints a
work order in the same shape nightly.py prints for reads. Selection is the same
arithmetic over the filesystem: a conflict appears here only while no ruling for
it exists, so a run that is interrupted resumes by being run again.

Run from the repository root, after conflicts.py:

    python3 A-2020-02093-MRV-FINAL_pdf_v3/passc.py <sandbox>

One line per adjudication, tab-separated:

    stem <TAB> field <TAB> model <TAB> brief <TAB> fields <TAB> slice <TAB> pdf <TAB> out

Only field conflicts are listed. A condition whose text is not on its cited page
and a field neither reader verified are both real work, but they are a different
job from choosing between two readings and contract_c.md does not describe them.
A conflict is also held back while either of its two reads is on a contract no
longer in force: re-reading can change the answers a ruling was made between.
The counts of both are printed.

Exit status is 0 while adjudications remain and 3 when none do.
"""
import json, os, re, sys

from stamp import EQUIVALENT, current, survey

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "nightly.json")
MODEL = "opus"                 # measured: a Sonnet adjudicator under-collects
NONE_OUTSTANDING = 3


def slug(field):
    """A field name as a filename component, reversibly enough to read."""
    return re.sub(r"[^a-z0-9]+", "_", field.lower()).strip("_")


def on_a_live_contract(sandbox):
    """Reader files read under a contract still in force, or equivalent to one.

    A ruling is made against two particular answers. Re-reading a document under
    a newer contract can change those answers, and the ruling would still be
    sitting there keyed to the field. So a document is not adjudicated until the
    reads underneath it are ones the corpus intends to keep.
    """
    ok = set(current().values()) | set(EQUIVALENT)
    return {f for h, files in survey(sandbox).items() if h in ok for f in files}


def orders_by_stem(sandbox):
    wave = json.load(open(f"{sandbox}/wave.json"))
    return {o["stem"]: o for o in wave}


def entries_as_written(out_dir, stem, tag, field):
    """One reader's answer for one field, with the pages it actually cited.

    Read off disk rather than taken from the build, which absolutises pages to
    place them in the workbook. The adjudicator is given the excerpt and the PDF
    of it, both numbered from 1, and must be given citations that match.
    """
    path = os.path.join(out_dir, f"{stem}.{tag}.json")
    if not os.path.exists(path):
        return []
    doc = json.load(open(path))
    return (doc.get("fields", {}).get(field) or {}).get("entries") or []


def briefs(sandbox):
    """Every unsettled field conflict, as (work order line, brief written)."""
    conflicts = json.load(open(f"{sandbox}/conflicts.json"))
    orders = orders_by_stem(sandbox)
    brief_dir, ruling_dir = f"{sandbox}/passc", f"{sandbox}/adjudicated"
    os.makedirs(brief_dir, exist_ok=True)

    live = on_a_live_contract(sandbox)
    lines, other, stale = [], 0, 0
    for c in conflicts:
        if not c["why"].startswith("different answers"):
            other += 1
            continue
        stem = c["document"].replace("#", "_")
        if not all(f"{stem}.{t}.json" in live for t in ("a1", "a2")):
            stale += 1
            continue
        order = orders.get(stem)
        if order is None:
            raise KeyError(f"{stem} is in conflicts.json but not in the work order")
        name = f"{stem}.{slug(c['field'])}.json"
        out = os.path.join(ruling_dir, name)
        if os.path.exists(out):
            continue                                  # already ruled on
        out_dir = os.path.dirname(order["out"])
        brief = {
            "document_id": c["document"],
            "field": c["field"],
            "pages": [1, order["last_page"] - order["first_page"] + 1],
            "disagreement": c["why"],
            "reader_1": entries_as_written(out_dir, stem, "a1", c["field"]),
            "reader_2": entries_as_written(out_dir, stem, "a2", c["field"]),
        }
        brief_path = os.path.join(brief_dir, name)
        json.dump(brief, open(brief_path, "w"), indent=1, ensure_ascii=False)
        lines.append((stem, c["field"], MODEL, brief_path,
                      order["fields"], order["slice"], order["pdf"], out))
    return lines, other, stale


if __name__ == "__main__":
    sandbox = sys.argv[1]
    lines, other, stale = briefs(sandbox)
    cap = json.load(open(CONFIG))["adjudications_per_night"]
    print(f"# {len(lines)} adjudications outstanding; {stale} waiting on a re-read; "
          f"{other} queue entries are a different job and are not listed")
    for line in lines[:cap]:
        print("\t".join(line))
    # On the full count, not the capped one: a cap of zero is a night that
    # adjudicates nothing, not a corpus with nothing left to adjudicate.
    sys.exit(NONE_OUTSTANDING if not lines else 0)
