"""Choose the reads for one night, and report when there are none left.

The driver that runs each night decides nothing. This does: it takes the work
order, removes every read whose output already exists, and prints the next few
in a fixed format. Selection is arithmetic over the filesystem, so it costs
nothing and cannot drift with whatever the driver happens to believe.

Run from the repository root:

    python3 A-2020-02093-MRV-FINAL_pdf_v3/nightly.py           the night's reads
    python3 A-2020-02093-MRV-FINAL_pdf_v3/nightly.py --status  what remains

A read already on disk is never selected again. Re-reading under a revised
contract is a deliberate act, not something a definition change triggers.

Exit status is 0 while work remains and 3 when the corpus is finished, so a
scheduled run can stop without a person deciding it is done.
"""
import json, os, sys
from itertools import groupby
from operator import itemgetter

from stamp import live, stamp_of

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CONFIG = os.path.join(HERE, "nightly.json")
WAVE = os.path.join(HERE, "staged", "wave.json")
FINISHED = 3


def load():
    cfg = json.load(open(CONFIG))
    wave = json.load(open(WAVE))
    for o in wave:
        o["_out_abs"] = os.path.join(ROOT, o["out"])
    return cfg, wave


def outstanding(wave):
    """Reads with no answer yet.

    A read is outstanding when its output is missing, and only then. A read
    taken under an earlier version of the contract still answers the page, so it
    does not become work again when a definition is reworded; refining a field
    would otherwise retire the whole corpus and the reading would never finish.
    Staleness is reported by `stale` and acted on deliberately, never by the
    selector.
    """
    return [o for o in wave if not os.path.exists(o["_out_abs"])]


def stale(wave):
    """Answers on disk produced under a contract that has since changed.

    Advisory. Worth knowing before trusting a measurement that compares fields
    across documents, and worth re-reading a sample of when a definition changes
    enough to be worth measuring — but it generates no work on its own.
    """
    ok = live()
    return [o for o in wave
            if os.path.exists(o["_out_abs"]) and stamp_of(o["_out_abs"]) not in ok]


def tonight(cfg, wave):
    """Whole documents, in work-order order, up to the night's cap.

    Whole documents rather than loose reads: both passes and both readers of one
    document belong together, and a half-read document cannot be combined or
    adjudicated until the rest of it arrives.
    """
    left = outstanding(wave)
    picked, docs = [], []
    for o in left:
        if o["stem"] not in docs:
            if len(docs) == cfg["documents_per_night"]:
                break
            docs.append(o["stem"])
        picked.append(o)
    return picked, docs, left


def batches(picked, limit):
    """Tonight's reads split so no batch exceeds the concurrency limit.

    Split between documents and never inside one. A document's reads belong
    together: they are combined with each other and nothing else, and a reader
    that fails is easier to place when the others ran beside it.
    """
    out, cur = [], []
    for _, group in groupby(picked, key=itemgetter("stem")):
        group = list(group)
        if cur and len(cur) + len(group) > limit:
            out.append(cur)
            cur = []
        cur.extend(group)
    if cur:
        out.append(cur)
    return out


if __name__ == "__main__":
    cfg, wave = load()
    picked, docs, left = tonight(cfg, wave)

    if "--status" in sys.argv:
        done = len(wave) - len(left)
        print(f"reads {done}/{len(wave)} done, {len(left)} outstanding")
        older = stale(wave)
        if older:
            print(f"{len(older)} of the {done} answered under an earlier contract "
                  f"(advisory — not selected for re-reading)")
        print(f"documents this run: {cfg['documents_per_night']}")
        print(f"rounds this night: {cfg['rounds_per_night']}")
        sys.exit(FINISHED if not left else 0)

    if not left:
        print("NOTHING OUTSTANDING — the corpus is fully read.")
        sys.exit(FINISHED)

    groups = batches(picked, cfg["concurrent_reads"])
    print(f"# {len(picked)} reads over {len(docs)} documents in {len(groups)} batch(es); "
          f"{len(left)} of {len(wave)} outstanding before tonight")
    for n, group in enumerate(groups, 1):
        print(f"# batch {n} of {len(groups)} — {len(group)} reads")
        for o in group:
            print(f"{o['stem']}\t{o['pass']}{o['reader']}\t{o['model']}\t{o['language']}\t"
                  f"{o['contract']}\t{o['slice']}\t{o['pdf']}\t{o['out']}")
