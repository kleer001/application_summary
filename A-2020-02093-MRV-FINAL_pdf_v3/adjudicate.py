"""Decide what a disagreement between two readers actually is.

Measured over the first eighteen documents, 26 of 664 answered fields disagreed
in a way that survived exact and containment matching. Reading all 26 against
the pages they cite, three were a misreading. The rest were one of two things:

  texture — the same fact quoted to a different length, or written with
            different spacing, punctuation or capitalisation. "three consecutive
            years" against "three consecutive years, to be initiated the year
            following the final year of the reintroduction plan".

  lapse   — one reader listed fewer of the items the other found, or stopped
            partway through a clause. Nothing is contradicted; something is
            missing.

Neither needs a person. A conflict does: two readers naming different figures
for the same field is the case this record exists to catch, and it is the only
one that reaches the queue.
"""
import difflib
import re

from norm import norm

TEXTURE_RATIO = 0.80          # two renderings of one passage
PAIR_RATIO = 0.75             # one entry against its opposite number


def _ratio(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()


def _twins(x, y):
    """One passage rendered two ways: one inside the other, or near-identical.

    Containment has to be tested as well as similarity. A short quote sitting
    inside a long one scores badly on a similarity ratio precisely because the
    long one says more, which is the case being recognised, not excluded.
    """
    if len(x) >= 8 and len(y) >= 8 and (x in y or y in x):
        return True
    return _ratio(x, y) >= PAIR_RATIO


def _pairs_up(sa, sb):
    """Every entry on the smaller side has a near-twin on the larger side."""
    small, large = (sa, sb) if len(sa) <= len(sb) else (sb, sa)
    used = set()
    for y in small:
        hit = next((x for x in large if x not in used and _twins(x, y)), None)
        if hit is None:
            return False
        used.add(hit)
    return True


def classify(sa, sb, qa=None, qb=None):
    """agree | texture | lapse | conflict.

    `qa`/`qb` are the folded quote sets. Two readers citing the same passages
    are looking at the same words, so any difference between their values is
    how they wrote it down — which is texture by definition, and needs no
    adjudicator. This was suggested by an adjudicator that had just spent a read
    confirming exactly that.
    """
    if qa and qb and qa == qb and sa != sb:
        return "texture"
    if sa == sb:
        return "agree"
    if not sa or not sb:
        return "lapse"
    if sa < sb or sb < sa:
        return "lapse"
    if _ratio(" ".join(sorted(sa)), " ".join(sorted(sb))) >= TEXTURE_RATIO:
        return "texture"
    if _pairs_up(sa, sb):
        return "texture" if len(sa) == len(sb) else "lapse"
    return "conflict"


def richer(ea, eb):
    """The answer carrying more of the document: more entries, then more text."""
    def weight(entries):
        return (len(entries), sum(len(str(e.get("value", ""))) for e in entries))
    return ea if weight(ea) >= weight(eb) else eb


def adjudicate(ea, eb):
    """Two readers' entries for one field.

    Returns (entries, verdict, note). `verdict` is the classification; a note is
    carried for everything except plain agreement, so that taking one reader
    over the other is always visible in the record rather than silent.
    """
    sa = {norm(e["value"]) for e in ea if e.get("value") not in (None, "")}
    sb = {norm(e["value"]) for e in eb if e.get("value") not in (None, "")}
    qa = {norm(e.get("quote", "")) for e in ea if e.get("quote")}
    qb = {norm(e.get("quote", "")) for e in eb if e.get("quote")}
    verdict = classify(sa, sb, qa, qb)

    if verdict == "agree":
        return (ea or eb), "agree", None
    if verdict == "texture":
        why = ("both readers cited the same passages" if qa and qa == qb
               else "same passage, quoted to different lengths")
        return richer(ea, eb), "texture", why
    if verdict == "lapse":
        kept = richer(ea, eb)
        return kept, "lapse", f"one reader listed {min(len(sa), len(sb))} of {max(len(sa), len(sb))}"
    return [], "conflict", f"different answers: {sorted(sa)[:2]} against {sorted(sb)[:2]}"
