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

Three kinds of brief are listed, all of them adjudications: a field two readers
answered differently, a number one read as a heading, and — carrying a question
rather than two candidates — a field neither reader verified or a condition whose
text is not on its cited page. The last kind is settled by reading the scan,
which the adjudicator is given, so it is work pass C takes rather than work that
leaves the pipeline. The count resting on a read taken under an earlier contract
is printed beside the total, as information.

Exit status is 0 while adjudications remain and 3 when none do.
"""
import functools, json, os, re, sys

from combine import number_key
from ids import stem_of
from stamp import live, survey

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "nightly.json")
MODEL = "opus"                 # measured: a Sonnet adjudicator under-collects

# The three questions contract_c.md describes, and which reads each rests on.
# An entry reaches an adjudicator because its reason says so, never because of
# how its `why` sentence is worded.
#
# "page" is the third kind. Where a conflict asks which of two answers the
# document supports, these ask what the document says at all: nobody produced a
# quote that verified, so there is nothing to choose between. An adjudicator is
# given the scan as well as the excerpt, which is what settles them — the same
# reading a reader does, done once more against the page.
KIND = {"conflict": "field", "heading_dispute": "heading",
        "neither_verified": "page", "condition_off_page": "page"}
READS = {"field": ("a1", "a2"), "heading": ("b1", "b2"),
         "page": ("a1", "a2")}          # overridden per entry for a condition
ADJUDICABLE = tuple(KIND)
NONE_OUTSTANDING = 3


def slug(field):
    """A field name as a filename component, reversibly enough to read."""
    return re.sub(r"[^a-z0-9]+", "_", field.lower()).strip("_")


def on_an_earlier_contract(sandbox):
    """Reader files read under a contract no longer in force.

    Counted and reported, never gated on. A ruling is made against the two
    answers actually on disk, and those are the answers the corpus keeps: reads
    are not re-taken because a definition was reworded. Gating adjudication on a
    live stamp would hold every conflict until a re-read that is never coming.
    """
    ok = live()
    return {f for h, files in survey(sandbox).items() if h not in ok for f in files}


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

    earlier = on_an_earlier_contract(sandbox)
    picked, other, stale = [], 0, 0
    for c in conflicts:
        if c["reason"] not in ADJUDICABLE:
            other += 1
            continue
        kind = KIND[c["reason"]]
        stem = stem_of(c["document"])
        reads = (("b1", "b2") if c["reason"] == "condition_off_page"
                 else READS[kind])
        if any(f"{stem}.{t}.json" in earlier for t in reads):
            stale += 1
        order = orders.get(stem)
        if order is None:
            raise KeyError(f"{stem} is in conflicts.json but not in the work order")
        name = f"{stem}.{slug(c['field'])}.json"
        if name in ruled:
            continue                                  # already ruled on
        picked.append((c, stem, order, name, kind))
    return picked, other, stale


def condition_brief(out_dir, stem, number):
    """A condition as each reader wrote it down, with the page each one cited.

    Both readers are shown because they may have cited different pages for the
    same text, which is itself the answer: one of them read the page number off
    a running header rather than the line.
    """
    seen = []
    for tag in ("b1", "b2"):
        for cond in read_out(out_dir, stem, tag).get("conditions") or []:
            if ".".join(str(x) for x in number_key(cond.get("number"))) == number:
                seen.append({"reader": tag, "number": cond.get("number"),
                             "page": cond.get("page"), "text": cond.get("text"),
                             "source": cond.get("source")})
    return seen


def write_brief(sandbox, c, stem, order, name, kind):
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
    if kind == "heading":
        number = c["number"]
        line, children = heading_brief(out_dir, stem, number)
        brief.update(question="Is this number a condition, or a heading for the "
                              "numbers beneath it?",
                     number=number, line=line, children=children)
    elif kind == "page":
        if c["reason"] == "condition_off_page":
            number = ".".join(str(x) for x in number_key(c["field"].split()[-1]))
            brief.update(question="This condition's text is not on the page it "
                                  "cites. What does the scan show, and on which "
                                  "page?",
                         number=number,
                         as_recorded=condition_brief(out_dir, stem, number))
        else:
            brief.update(question="Neither reader produced a quote that verified. "
                                  "What does the document say for this field?",
                         reader_1=entries_as_written(out_dir, stem, "a1", c["field"]),
                         reader_2=entries_as_written(out_dir, stem, "a2", c["field"]))
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
    cfg = json.load(open(CONFIG))
    cap, width = cfg["adjudications_per_night"], cfg["concurrent_reads"]
    tonight = picked[:cap]
    # Batched for the same reason the reads are: adjudicators are subagents on
    # the same concurrency ceiling, and a batch dispatched on top of a running
    # one has its excess rejected rather than queued. The lines are independent
    # of each other, so this splits anywhere, unlike a document's reads.
    groups = [tonight[i:i + width] for i in range(0, len(tonight), width)]
    print(f"# {len(picked)} adjudications outstanding "
          f"({stale} resting on a read taken under an earlier contract); "
          f"{other} queue entries are a different job and are not listed")
    print(f"# {len(tonight)} to settle tonight in {len(groups)} batch(es)")
    for n, group in enumerate(groups, 1):
        print(f"# batch {n} of {len(groups)} — {len(group)} adjudications")
        for args in group:
            print("\t".join(write_brief(sandbox, *args)))
    # On the full count, not the capped one: a cap of zero is a night that
    # adjudicates nothing, not a corpus with nothing left to adjudicate.
    sys.exit(NONE_OUTSTANDING if not picked else 0)
