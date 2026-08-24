"""Record which contract a reader's answer was produced under.

A reader file that does not say which specification it followed cannot be told
apart from one that followed a different specification, and a corpus read across
several versions then has to be re-read whole because nobody can identify the
stale part. Stamping is deterministic and costs nothing: the driver applies it
after a read lands, so it does not depend on a reader remembering to.

    stamp.py <sandbox>              stamp every unstamped file in out/
    stamp.py <sandbox> --report     what versions the sandbox holds
    stamp.py <sandbox> --stale      files not on the contracts now in force
"""
import hashlib, json, os, sys

import paths

HERE = os.path.dirname(os.path.abspath(__file__))
# What a pass reads its question from. Pass A's question is the contract and the
# field specification together: a field definition settles what a reader
# extracts and how it is written down exactly as the contract does, so a
# specification change that left the stamp where it was would leave every
# earlier answer marked current while it answered a different question -- the
# silent case this stamp exists to prevent. Pass B enumerates conditions under
# contract_b and carries no fields at all, so the specification is not part of
# its stamp and a change to it does not cost a pass B re-read.
PASS_SOURCES = {"a": ("contract_a.md", "fields.json"), "b": ("contract_b.md",)}

# Contract versions whose differences from the one in force cannot change an
# answer, so answers produced under them need no re-reading. A hash goes here
# only with the reason it is harmless; anything touching what to extract, how to
# quote it, or the shape written out does not belong here.
EQUIVALENT = {}

# "65cf28db2fd3" was listed here and has been withdrawn. It was equivalent to
# the pass A contract as it then stood, and that equivalence was about the
# contract alone. The field specification is now part of pass A's stamp, and it
# has since changed: monitoring_duration no longer prescribes which form of
# words an answer must take, and monitoring_frequency now bounds the span of the
# quote. Both settle what a reader writes down, so an answer given before them
# is not the answer that would be given now. Every pass A read taken before this
# is stale.

# Both earlier pass B hashes were listed here and have been withdrawn. They were
# equivalent to the pass B contract as it then stood; they are not equivalent to
# the one in force, which settles what a condition is — a specific individual
# deliverable, so a line that only introduces the deliverables below it is a
# heading. That changes which numbers earn an entry, and unlike the
# not-applicable rule it cannot be applied to an answer after the fact: whether a
# parent carried a deliverable of its own is not recoverable from an entry a
# reader chose not to write. Every pass B read taken before it is stale.


def out_dir(sandbox):
    """Where a sandbox keeps reader output."""
    return paths.out_dir(sandbox)


def sha(*files):
    """One hash over several files, in the order given.

    Not named `paths`: this module imports a module of that name.
    """
    h = hashlib.sha256()
    for path in files:
        h.update(open(path, "rb").read())
    return h.hexdigest()[:12]


def current():
    return {p: sha(*(os.path.join(HERE, f) for f in files))
            for p, files in PASS_SOURCES.items()}


def pass_of(name):
    """`<stem>.a1.json` -> `a`. The pass is in the suffix the work order assigns."""
    return paths.pass_of(name)


def stamp(sandbox):
    now, done, already = current(), 0, 0
    od = out_dir(sandbox)
    for name in sorted(os.listdir(od)):
        if not name.endswith(".json"):
            continue
        path = f"{od}/{name}"
        doc = json.load(open(path))
        if "contract" in doc:
            already += 1
            continue
        doc["contract"] = now[pass_of(name)]
        json.dump(doc, open(path, "w"), indent=1, ensure_ascii=False)
        done += 1
    return done, already


def stamp_of(path):
    """The contract a reader file records, or UNSTAMPED if it records none.

    Unparseable JSON is not answered here. A corrupt reader output is a real
    fault and reporting it as unstamped would quietly turn it into a re-read and
    file it in superseded/ as though it had merely been written under an older
    contract.
    """
    return json.load(open(path)).get("contract", "UNSTAMPED")


def live():
    """Stamps whose answers still stand: in force, or equivalent to one.

    Selecting reads, adjudicating them and reporting on them must agree about
    which answers are stale, so the set is defined once here beside EQUIVALENT
    rather than rebuilt by each caller.
    """
    return set(current().values()) | set(EQUIVALENT)


def survey(sandbox):
    seen, od = {}, out_dir(sandbox)
    for name in sorted(os.listdir(od)):
        if name.endswith(".json"):
            seen.setdefault(stamp_of(f"{od}/{name}"), []).append(name)
    return seen


if __name__ == "__main__":
    sandbox = sys.argv[1]
    now = current()
    if "--report" in sys.argv or "--stale" in sys.argv:
        seen = survey(sandbox)
        print("contracts now in force:", ", ".join(f"{p}={h}" for p, h in now.items()))
        for h, files in sorted(seen.items(), key=lambda kv: -len(kv[1])):
            mark = ("in force" if h in now.values()
                    else f"equivalent — {EQUIVALENT[h]}" if h in EQUIVALENT
                    else "STALE, needs re-reading")
            print(f"  {h:12s} {len(files):4d} files   {mark}")
        if "--stale" in sys.argv:
            ok = live()
            stale = [f for h, fs in seen.items() if h not in ok for f in fs]
            print(f"\n{len(stale)} files not on a contract in force")
            for f in stale:
                print(f"  {f}")
    else:
        done, already = stamp(sandbox)
        print(f"stamped {done} files, {already} already carried a stamp")
        print("contracts now in force:", ", ".join(f"{p}={h}" for p, h in now.items()))
