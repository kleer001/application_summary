"""Where the pipeline's files are, and what their names mean.

Three facts were spelled out in six modules apiece and had to agree for any of
them to be right: that the work order's paths are relative to the repository
root, that a reader's answer is `<sandbox>/out/<stem>.<pass><reader>.json`, and
that a document is finished when all of its reads are on disk. They agree here
instead.

The repository-root rule is the one that bit. `status.py` read the work order's
`out` as relative to the current directory, so run from inside the pipeline
directory it reported 516 of 516 reads outstanding — no error, just a confident
account of a corpus it could not see.
"""
import json, os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

FIELD_READS = ("a1", "a2")          # pass A: the fields, two independent readers
CONDITION_READS = ("b1", "b2")      # pass B: the conditions
ALL_READS = FIELD_READS + CONDITION_READS
READS_PER_DOCUMENT = len(ALL_READS)


def prior_summary():
    """The prior workbook, wherever this clone keeps it.

    release.json records the path the release was built from, which is absolute
    and on one machine. Every clone still has the file, under the release
    directory at the repository root, so look for it there rather than failing
    with a path nobody else can have. Scoring that only runs on the author's
    laptop is scoring that does not run -- and so is a link between file numbers
    and prior rows, which is what `prior_rows.py` was doing: it read the recorded
    path straight out of release.json and died on a clone.

    Here rather than in score.py because two modules need it and this is where
    the pipeline's path rules live.
    """
    recorded = json.load(open(os.path.join(HERE, "release.json")))["prior_summary"]
    if os.path.exists(recorded):
        return recorded
    name = os.path.basename(recorded)
    for base, dirs, files in os.walk(ROOT):
        dirs.sort()
        if name in files:
            return os.path.join(base, name)
    return recorded


def resolve(path):
    """A work-order path, as an absolute one.

    Paths in wave.json are written relative to the repository root so the same
    order works from a clone anywhere. Reading them relative to the working
    directory silently finds nothing.
    """
    return path if os.path.isabs(path) else os.path.join(ROOT, path)


def out_dir(sandbox):
    """Where a sandbox keeps reader output."""
    return os.path.join(sandbox, "out")


def reader_path(sandbox, stem, tag):
    """One reader's answer for one document."""
    return os.path.join(out_dir(sandbox), f"{stem}.{tag}.json")


def tag_of(name):
    """`19-HCAA-00130_250.b2.json` -> `b2`."""
    return os.path.basename(name).rsplit(".", 2)[1]


def pass_of(name):
    """`19-HCAA-00130_250.b2.json` -> `b`."""
    return tag_of(name)[0]


def reads_on_disk(sandbox):
    """How many reads each document has, by stem."""
    d = out_dir(sandbox)
    return Counter(f.split(".")[0] for f in os.listdir(d) if f.endswith(".json"))


def complete_stems(sandbox):
    """Documents every reader has answered.

    A half-read document cannot be combined or adjudicated, so the build, the
    conflict queue and the quality gate must all mean the same thing by "read" —
    and they each used to count to four on their own.
    """
    have = reads_on_disk(sandbox)
    return {stem for stem, n in have.items() if n == READS_PER_DOCUMENT}
