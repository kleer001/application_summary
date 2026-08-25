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

from norm import norm, wordset

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
    """Every entry on the smaller side has a near-twin on the larger side.

    Both sides are sorted before matching. They arrive as sets, and pairing them
    off greedily means the first twin found wins the entry it matched — so with
    set iteration order the verdict depended on the hash seed, and the same two
    readers could be a conflict on one run and texture on the next. Measured
    over the reads banked so far, one field in the queue moved between runs.

    The matching stays greedy, which can fail to pair sides that a perfect
    matching would. That direction is the safe one: it reports a conflict and a
    person looks at it.
    """
    small, large = (sa, sb) if len(sa) <= len(sb) else (sb, sa)
    small, large = sorted(small), sorted(large)
    used = set()
    for y in small:
        hit = next((x for x in large if x not in used and _twins(x, y)), None)
        if hit is None:
            return False
        used.add(hit)
    return True


def classify(sa, sb, qa=None, qb=None, wa=None, wb=None):
    """agree | texture | lapse | conflict.

    `qa`/`qb` are the folded quote sets. Two readers citing the same passages
    are looking at the same words, so any difference between their values is
    how they wrote it down — which is texture by definition, and needs no
    adjudicator. This was suggested by an adjudicator that had just spent a read
    confirming exactly that.

    `wa`/`wb` are the word sets of the same values. They cannot be recovered
    from `sa`/`sb`, which have had their word boundaries folded away, so they are
    built from the raw values by the caller.

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

    # Last, the same question asked of words rather than characters. Three
    # differences survive everything above because folding to one string keeps
    # character order: the same items listed in a different order, a figure
    # written once with its unit and once without, and one reader splitting a
    # clause into entries the other ran together. None of them is two readers
    # naming different facts, which is the only thing a person is needed for.
    #
    # The risk this accepts is a pair of values built from the same words with
    # the pairings swapped - "destruction 650, alteration 180" against
    # "destruction 180, alteration 650" - which reads as texture here. No such
    # pair appears in the reads banked so far, and the guard against one is the
    # page citation the value carries, which verification checks separately.
    if wa and wb:
        if wa == wb:
            return "texture"                  # same words, written in another order
        if wa < wb or wb < wa:
            return "lapse"                    # one side said everything the other did, and more
    return "conflict"


def richer(ea, eb):
    """The answer carrying more of the document: more entries, then more
    attribution, then more text.

    Attribution counts before text length because it is the one part of an
    answer that cannot be recovered later. Where one reader filed a figure under
    the authorization the document attributes it to and the other only recorded
    the figure, the first read the page more completely, and dropping to the
    second loses something no later pass can put back."""
    def weight(entries):
        return (len(entries),
                sum(1 for e in entries if e.get("authorization")),
                sum(len(str(e.get("value", ""))) for e in entries))
    return ea if weight(ea) >= weight(eb) else eb


def filed(entries):
    """Where each value was filed, for the entries that say.

    A letter can grant several numbered authorizations at once and sort its
    impacts under them by heading. Both sides are folded, so an authorization
    written two ways is one authorization here as it is everywhere else.
    """
    return {norm(e["value"]): norm(e["authorization"]) for e in entries
            if e.get("authorization") and e.get("value") not in (None, "")}


def crossed(aa, ab):
    """Did the two readers file a value they both attributed differently?

    Only values both of them attributed can disagree. A reader who attributed
    four of the five figures the other did has said less, not something else,
    and that is a lapse for the rules below to settle rather than a contradiction.

    This is asked before `classify`, and separately from it, because every rule
    in there compares what was quoted. Which authorization a figure belongs to is
    not in its quote — it is the heading the figure sits under — so two readers
    can cite one passage word for word and still have filed it against different
    authorizations. Left to `classify` that is texture, settled with no
    adjudicator: the swapped-pairings risk noted there, arriving by another road.
    """
    return any(aa[v] != ab[v] for v in aa.keys() & ab.keys())


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
    # Built here, from the values before folding: word boundaries are gone by
    # the time a value has been through `norm`.
    wa = set().union(*[wordset(e["value"]) for e in ea
                       if e.get("value") not in (None, "")] or [set()])
    wb = set().union(*[wordset(e["value"]) for e in eb
                       if e.get("value") not in (None, "")] or [set()])
    aa, ab = filed(ea), filed(eb)
    if crossed(aa, ab):
        return [], "conflict", f"the same figure filed against different authorizations"
    verdict = classify(sa, sb, qa, qb, wa, wb)

    if verdict == "agree":
        # Equal values can still differ in where they were filed, and only one
        # side may have said. `richer` prefers the reader who did.
        return (richer(ea, eb) if aa or ab else (ea or eb)), "agree", None
    if verdict == "texture":
        why = ("both readers cited the same passages" if qa and qa == qb
               else "same passage, quoted to different lengths")
        return richer(ea, eb), "texture", why
    if verdict == "lapse":
        kept = richer(ea, eb)
        return kept, "lapse", f"one reader listed {min(len(sa), len(sb))} of {max(len(sa), len(sb))}"
    return [], "conflict", f"different answers: {sorted(sa)[:2]} against {sorted(sb)[:2]}"
