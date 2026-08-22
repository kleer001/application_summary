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
import functools, json, os, re, sys

from combine import number_key
from ids import stem_of
from stamp import live, survey

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
    ok = live()
    return {f for h, files in survey(sandbox).items() if h in ok for f in files}


def orders_by_stem(sandbox):
    wave = json.load(open(f"{sandbox}/wave.json"))
    return {o["stem"]: o for o in wave}


@functools.lru_cache(maxsize=64)
def read_out(out_dir, stem, tag):
    """One reader's output, or an empty document where it wrote none.

    Cached: a document with sixteen heading disputes would otherwise parse the
    same two condition files sixteen times over.
    """
    path = os.path.join(out_dir, f"{stem}.{tag}.json")
    return json.load(open(path)) if os.path.exists(path) else {}


def entries_as_written(out_dir, stem, tag, field):
    """One reader's answer for one field, with the pages it actually cited.

    Read off disk rather than taken from the build, which absolutises pages to
    place them in the workbook. The adjudicator is given the excerpt and the PDF
    of it, both numbered from 1, and must be given citations that match.
    """
    fields = read_out(out_dir, stem, tag).get("fields") or {}
    return (fields.get(field) or {}).get("entries") or []


def heading_brief(out_dir, stem, number):
    """The disputed line and the numbers beneath it, from whichever reader kept them.

    A reader that read the line as a heading did not write it down, so its text
    comes from the one that did. The children come from both, because either may
    have recorded a given child and the adjudicator needs the whole family to see
    whether the parent binds anything they do not.
    """
    line, children = None, {}
    for tag in ("b1", "b2"):
        for c in read_out(out_dir, stem, tag).get("conditions") or []:
            num = ".".join(str(x) for x in number_key(c.get("number")))
            entry = {"number": c.get("number"), "page": c.get("page"), "text": c.get("text")}
            if num == number and line is None:
                line = entry
            elif num.startswith(number + "."):
                children.setdefault(num, entry)
    return line, [children[k] for k in sorted(children, key=number_key)]


def outstanding(sandbox):
    """Every unsettled conflict an adjudicator could take, in work-order order.

    Selection reads the queue, the rulings already on disk and the contract
    stamps, and never opens a reader file. Briefing costs several file loads, so
    only what the night will actually dispatch is briefed — the backlog is
    counted, not written out.
    """
    conflicts = json.load(open(f"{sandbox}/conflicts.json"))
    orders = orders_by_stem(sandbox)
    ruling_dir = f"{sandbox}/adjudicated"
    ruled = set(os.listdir(ruling_dir)) if os.path.isdir(ruling_dir) else set()

    on_contract = on_a_live_contract(sandbox)
    picked, other, stale = [], 0, 0
    for c in conflicts:
        heading = c["field"].startswith("heading ")
        if not heading and not c["why"].startswith("different answers"):
            other += 1
            continue
        stem = stem_of(c["document"])
        reads = ("b1", "b2") if heading else ("a1", "a2")
        if not all(f"{stem}.{t}.json" in on_contract for t in reads):
            stale += 1
            continue
        order = orders.get(stem)
        if order is None:
            raise KeyError(f"{stem} is in conflicts.json but not in the work order")
        name = f"{stem}.{slug(c['field'])}.json"
        if name in ruled:
            continue                                  # already ruled on
        picked.append((c, stem, order, name, heading))
    return picked, other, stale


def write_brief(sandbox, c, stem, order, name, heading):
    """The brief for one adjudication, and its line of the work order."""
    brief_dir = f"{sandbox}/passc"
    os.makedirs(brief_dir, exist_ok=True)
    out_dir = os.path.dirname(order["out"])
    brief = {
        "document_id": c["document"],
        "field": c["field"],
        "pages": [1, order["last_page"] - order["first_page"] + 1],
        "disagreement": c["why"],
    }
    if heading:
        number = c["field"].split(" ", 1)[1]
        line, children = heading_brief(out_dir, stem, number)
        brief.update(question="Is this number a condition, or a heading for the "
                              "numbers beneath it?",
                     number=number, line=line, children=children)
    else:
        brief.update(reader_1=entries_as_written(out_dir, stem, "a1", c["field"]),
                     reader_2=entries_as_written(out_dir, stem, "a2", c["field"]))
    brief_path = os.path.join(brief_dir, name)
    json.dump(brief, open(brief_path, "w"), indent=1, ensure_ascii=False)
    return (stem, c["field"], MODEL, brief_path,
            order["fields"], order["slice"], order["pdf"],
            os.path.join(sandbox, "adjudicated", name))


if __name__ == "__main__":
    sandbox = sys.argv[1]
    picked, other, stale = outstanding(sandbox)
    cap = json.load(open(CONFIG))["adjudications_per_night"]
    print(f"# {len(picked)} adjudications outstanding; {stale} waiting on a re-read; "
          f"{other} queue entries are a different job and are not listed")
    for args in picked[:cap]:
        print("\t".join(write_brief(sandbox, *args)))
    # On the full count, not the capped one: a cap of zero is a night that
    # adjudicates nothing, not a corpus with nothing left to adjudicate.
    sys.exit(NONE_OUTSTANDING if not picked else 0)
