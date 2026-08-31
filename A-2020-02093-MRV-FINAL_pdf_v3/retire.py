"""Retire reads, and the rulings resting on them, so they can be read again.

A read already on disk is never re-taken by a night. Selection asks whether an
answer is missing, not whether its stamp has moved, because refining the question
is how the reading gets better and gating on a live stamp would retire the corpus
at every edit. Retiring a read is therefore how a re-read is asked for, and it is
a decision taken by hand, deliberately, never by the nightly.

**A ruling has to move with the reads it was made against.** `passc.py` skips any
conflict whose ruling file already exists, and `build.py` prefers a ruling's
answer to a reader's. Retire two reads and leave their ruling behind, and that
ruling -- a verdict reached by weighing two answers that no longer exist -- is
applied, silently, to the two that replace them. It would not be reported, and it
would not look wrong in the workbook. This is the reason the tool exists rather
than a `mv`.

Which reads a ruling rests on is written in its own `field`. `condition 4.2` and
`heading 3.1` were settled from the pass B reads; everything else -- a field
conflict, a field neither reader verified -- from pass A. That is the same split
`passc.READS` uses to brief an adjudicator.

Nothing is deleted. Reads and rulings both move to `superseded/`, named for the
contract they were taken under, so a retirement can be read back and undone.

    retire.py <sandbox> --stems 19-HQUE-00077_760,20-HMAR-00098_651
    retire.py <sandbox> --stale                 every read on a superseded stamp
    retire.py <sandbox> --stale --pass b        the condition reads only
    retire.py <sandbox> --stale --split tune    the tuning half only

Prints what it would do and changes nothing unless `--yes` is given.
"""
import json, os, shutil, sys

from ids import corrected
from stamp import live, stamp_of

PASS_A, PASS_B = ("a1", "a2"), ("b1", "b2")


def rests_on(field):
    """Which pass produced the reads a ruling was made against."""
    return "b" if str(field).startswith(("condition ", "heading ")) else "a"


def tags_for(which):
    return {"a": PASS_A, "b": PASS_B, "both": PASS_A + PASS_B}[which]


def stale_reads(sandbox):
    """Reads whose stamp is not one still in force."""
    ok, out = live(), []
    d = f"{sandbox}/out"
    for name in sorted(os.listdir(d)):
        if name.endswith(".json") and stamp_of(f"{d}/{name}") not in ok:
            out.append(name)
    return out


def plan(sandbox, wanted):
    """The reads and rulings that would move, for {stem: passes to retire}.

    Taken per pass, not per document. The two passes ask different questions
    under different contracts, and a document whose field reads are superseded
    while its condition reads are current needs only the first re-read; retiring
    both would spend eight reads where four were called for.
    """
    out_d = f"{sandbox}/out"
    reads = [(stem, t) for stem in sorted(wanted) for p in sorted(wanted[stem])
             for t in tags_for(p) if os.path.exists(f"{out_d}/{stem}.{t}.json")]

    rulings, rule_d = [], f"{sandbox}/adjudicated"
    if os.path.isdir(rule_d):
        for name in sorted(os.listdir(rule_d)):
            if not name.endswith(".json"):
                continue
            stem = name.split(".")[0]
            if stem not in wanted:
                continue
            field = json.load(open(f"{rule_d}/{name}")).get("field", "")
            # Only the rulings whose own reads are going. A condition ruling
            # survives a pass A retirement untouched, and should.
            if rests_on(field) in wanted[stem]:
                rulings.append((stem, name, field))
    return reads, rulings


def move(sandbox, reads, rulings):
    sup = f"{sandbox}/superseded"
    os.makedirs(sup, exist_ok=True)
    for stem, tag in reads:
        src = f"{sandbox}/out/{stem}.{tag}.json"
        shutil.move(src, f"{sup}/{stem}.{tag}.{stamp_of(src)}.json")
    for stem, name, _ in rulings:
        src = f"{sandbox}/adjudicated/{name}"
        shutil.move(src, f"{sup}/{name[:-5]}.ruling.json")


def main():
    sandbox = sys.argv[1]
    argv = sys.argv[2:]

    def opt(flag, default=None):
        return argv[argv.index(flag) + 1] if flag in argv else default

    which = opt("--pass", "both")
    if which not in ("a", "b", "both"):
        raise SystemExit("--pass takes a, b or both")

    passes = {"a", "b"} if which == "both" else {which}
    if "--stems" in argv:
        wanted = {s.strip(): set(passes)
                  for s in opt("--stems").split(",") if s.strip()}
    elif "--stale" in argv:
        # Per pass: a read is stale or it is not, and its neighbour in the other
        # pass has nothing to do with it.
        wanted = {}
        for name in stale_reads(sandbox):
            stem, tag = name.split(".")[0], name.split(".")[1]
            p = "a" if tag in PASS_A else "b"
            if p in passes:
                wanted.setdefault(stem, set()).add(p)
    else:
        raise SystemExit("give --stems or --stale")

    half = opt("--split")
    if half:
        # A stem is <file number>_<first page>, and the split is keyed on file
        # numbers -- corrected ones, because a segment keyed on the wrong number
        # is filed under the right one everywhere else and must be here too.
        here = os.path.dirname(os.path.abspath(__file__))
        keep = set(json.load(open(f"{here}/split.json"))[half])
        wanted = {s: p for s, p in wanted.items()
                  if corrected(s, s.rsplit("_", 1)[0]) in keep}

    reads, rulings = plan(sandbox, wanted)
    print(f"{len(reads)} reads over {len({s for s, _ in reads})} documents, "
          f"and {len(rulings)} rulings resting on them")
    for s, t in reads[:10]:
        print(f"   read   {s}.{t}")
    if len(reads) > 10:
        print(f"   ... and {len(reads) - 10} more")
    for s, n, f in rulings[:10]:
        print(f"   ruling {n}   ({f})")
    if len(rulings) > 10:
        print(f"   ... and {len(rulings) - 10} more")

    if "--yes" not in argv:
        print("\nnothing moved. pass --yes to retire these.")
        return
    move(sandbox, reads, rulings)
    print(f"\nmoved to {sandbox}/superseded/. "
          f"nightly.py --status will now count these reads as outstanding.")


if __name__ == "__main__":
    main()
