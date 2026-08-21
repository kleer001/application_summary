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

HERE = os.path.dirname(os.path.abspath(__file__))
PASS_CONTRACT = {"a": "contract_a.md", "b": "contract_b.md"}

# Contract versions whose differences from the one in force cannot change an
# answer, so answers produced under them need no re-reading. A hash goes here
# only with the reason it is harmless; anything touching what to extract, how to
# quote it, or the shape written out does not belong here.
EQUIVALENT = {
    "65cf28db2fd3": "pass A, differs only in the reply a reader is asked for",
    "08ed9905cc09": "pass B, differs only in the reply a reader is asked for",
    "b6885a580b3d": ("pass B, before the not-applicable rule was written down; "
                     "combine.py drops those items from every read whatever the "
                     "reader did, so the workbook is the same either way"),
}


def out_dir(sandbox):
    """Where a sandbox keeps reader output.

    A sandbox staged by `wave.py` keeps it in `out/`; the repository keeps the
    accumulated run in `run2/out/`. Resolve rather than assume — guessing wrong
    fails at the end of a night, after the reads are already paid for.
    """
    for candidate in (f"{sandbox}/out", f"{sandbox}/run2/out"):
        if os.path.isdir(candidate):
            return candidate
    raise SystemExit(f"no output directory under {sandbox} (tried out/, run2/out/)")


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:12]


def current():
    return {p: sha(os.path.join(HERE, f)) for p, f in PASS_CONTRACT.items()}


def pass_of(name):
    """`<stem>.a1.json` -> `a`. The pass is in the suffix the work order assigns."""
    return name.rsplit(".", 2)[1][0]


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


def survey(sandbox):
    seen, od = {}, out_dir(sandbox)
    for name in sorted(os.listdir(od)):
        if name.endswith(".json"):
            doc = json.load(open(f"{od}/{name}"))
            seen.setdefault(doc.get("contract", "UNSTAMPED"), []).append(name)
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
            ok = set(now.values()) | set(EQUIVALENT)
            stale = [f for h, fs in seen.items() if h not in ok for f in fs]
            print(f"\n{len(stale)} files not on a contract in force")
            for f in stale:
                print(f"  {f}")
    else:
        done, already = stamp(sandbox)
        print(f"stamped {done} files, {already} already carried a stamp")
        print("contracts now in force:", ", ".join(f"{p}={h}" for p, h in now.items()))
