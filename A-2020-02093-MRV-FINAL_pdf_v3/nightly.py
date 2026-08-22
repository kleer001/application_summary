"""Choose the reads for one night, and report when there are none left.

The driver that runs each night decides nothing. This does: it takes the work
order, removes every read whose output already exists, and prints the next few
in a fixed format. Selection is arithmetic over the filesystem, so it costs
nothing and cannot drift with whatever the driver happens to believe.

Run from the repository root:

    python3 A-2020-02093-MRV-FINAL_pdf_v3/nightly.py           the night's reads
    python3 A-2020-02093-MRV-FINAL_pdf_v3/nightly.py --status  what remains

Exit status is 0 while work remains and 3 when the corpus is finished, so a
scheduled run can stop without a person deciding it is done.
"""
import json, os, shutil, sys
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
    """Reads with no answer, and reads whose answer is no longer current.

    A read is outstanding when its output is missing, and equally when the
    output was produced under a contract that has since changed in a way that
    can alter the answer. Without the second test a contract change is a
    decision nothing acts on: the files are all present, so nothing is ever
    selected, and the corpus keeps its old answers for good.
    """
    ok = live()
    return [o for o in wave
            if not os.path.exists(o["_out_abs"]) or stamp_of(o["_out_abs"]) not in ok]


def retire(picked):
    """Move a superseded answer aside so the re-read has somewhere to land.

    Kept rather than overwritten: it was a real reading of the page, and which
    contract a figure came from is part of its provenance. The destination comes
    from each file's own path, so nothing has to reconstruct where the sandbox is.
    """
    moved = []
    for o in picked:
        path = o["_out_abs"]
        if not os.path.exists(path):
            continue
        dest = os.path.join(os.path.dirname(os.path.dirname(path)), "superseded")
        os.makedirs(dest, exist_ok=True)
        # Named by the contract that produced it. A document read three times
        # under three contracts supersedes twice, and moving each to its plain
        # name would leave only the last — losing the very thing this directory
        # is for. The stamp also says, from the filename alone, which version of
        # the specification an old answer was given under.
        stem, _, ext = os.path.basename(path).rpartition(".")
        tag = stamp_of(path)
        target = os.path.join(dest, f"{stem}.{tag}.{ext}")
        n = 2
        while os.path.exists(target):
            target = os.path.join(dest, f"{stem}.{tag}.{n}.{ext}")
            n += 1
        shutil.move(path, target)
        moved.append(os.path.basename(target))
    return moved


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
        print(f"documents this run: {cfg['documents_per_night']}")
        sys.exit(FINISHED if not left else 0)

    if not left:
        print("NOTHING OUTSTANDING — the corpus is fully read.")
        sys.exit(FINISHED)

    if "--retire" in sys.argv:
        moved = retire(picked)
        if moved:
            print(f"# retired {len(moved)} superseded answer(s) to superseded/")

    groups = batches(picked, cfg["concurrent_reads"])
    print(f"# {len(picked)} reads over {len(docs)} documents in {len(groups)} batch(es); "
          f"{len(left)} of {len(wave)} outstanding before tonight")
    for n, group in enumerate(groups, 1):
        print(f"# batch {n} of {len(groups)} — {len(group)} reads")
        for o in group:
            print(f"{o['stem']}\t{o['pass']}{o['reader']}\t{o['model']}\t{o['language']}\t"
                  f"{o['contract']}\t{o['slice']}\t{o['pdf']}\t{o['out']}")
