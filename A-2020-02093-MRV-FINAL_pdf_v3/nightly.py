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
import json, os, sys

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
    return [o for o in wave if not os.path.exists(o["_out_abs"])]


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

    print(f"# {len(picked)} reads over {len(docs)} documents; "
          f"{len(left)} of {len(wave)} outstanding before tonight")
    for o in picked:
        print(f"{o['stem']}\t{o['pass']}{o['reader']}\t{o['model']}\t{o['language']}\t"
              f"{o['contract']}\t{o['slice']}\t{o['pdf']}\t{o['out']}")
