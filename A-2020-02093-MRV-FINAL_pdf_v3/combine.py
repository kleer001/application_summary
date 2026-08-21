"""Turn two readers' answers into one answer, or into a queue entry.

Agreement for bounded fields, union for enumeration. The asymmetry is the point:
two readers naming different figures have disagreed, but two readers listing
different numbers of conditions have not — one of them stopped early.
"""
import re

from adjudicate import adjudicate

OK = ("pass", "null", "QUEUE")
from norm import norm as fold

def values(field):
    return [e for e in (field or {}).get("entries") or []
            if isinstance(e, dict) and e.get("value") not in (None, "")]


def covers(sa, sb):
    """Does every answer in sb appear inside some answer in sa?

    Two readers quoting the same clause to different lengths are not two
    readings. One quoted it; the other abbreviated, which the contract forbids
    but which still names the same fact on the same page. Containment is checked
    entry by entry, on the folded text, where character order survives and
    spacing and punctuation do not.
    """
    if not sa or not sb or len(sa) < len(sb):
        return False
    used = set()
    for y in sorted(sb):                               # greedy over a set is seed-dependent
        if len(y) < 8:
            return False                       # too short to be evidence of anything
        hit = next((x for x in sorted(sa) if x not in used and (y in x or x in y)), None)
        if hit is None:
            return False
        used.add(hit)
    return True


def contains(sa, sb):
    """Either side wholly accounted for by the other."""
    return covers(sa, sb) or covers(sb, sa)


def combine_field(fa, fb, verdict_a, verdict_b):
    """One field, two readers.

    Returns (entries, note, resolved). A note records what happened; `resolved`
    says whether the rules settled it. Only the unresolved need a person, so the
    two are kept apart rather than filed together as "queue".
    """
    # Three verdicts are answers, not failures. "null" is the reader saying the
    # document is silent. "QUEUE" is a quote the reader read off the scan that
    # the OCR layer does not carry — the expected outcome on a mangled page, and
    # the reason the scan is given to readers at all. Only REJECT and MALFORMED
    # are a failure to verify.
    ok_a, ok_b = verdict_a in OK, verdict_b in OK
    ea, eb = values(fa) if ok_a else [], values(fb) if ok_b else []

    if not ok_a and not ok_b:
        return [], f"neither reader verified ({verdict_a} / {verdict_b})", False
    if not ea and not eb:
        ra = (fa or {}).get("reason")
        rb = (fb or {}).get("reason")
        if ok_a and ok_b and ra != rb:
            return [], f"both null, different reasons: {ra} / {rb}", False
        return [], None, True                              # agreed null

    entries, verdict, note = adjudicate(ea, eb)
    return entries, note, verdict != "conflict"


# A numbered item answering "not applicable" states no requirement, and a
# condition is a requirement of the authorization. Observed as a label followed
# by the marker, in both languages and with the accent and the full stop coming
# and going: 29 such entries over 18 distinct wordings in the reads banked so
# far. The payload is what follows the label, so a requirement that merely
# mentions one of these words is untouched.
NOT_APPLICABLE = {"na", "n/a", "notapplicable", "notapplicablena", "so", "s/o",
                  "nesappliquepas", "sansobjet", "aucun", "aucune", "nil", "none"}


def states_a_requirement(text):
    """False for a numbered item whose whole answer is "not applicable"."""
    t = (text or "").strip()
    payload = t.rsplit(":", 1)[1] if ":" in t else t
    folded = re.sub(r"[^a-z0-9/]", "", payload.lower().replace("\u2019", "").replace("'", ""))
    return folded not in NOT_APPLICABLE


def norm_number(n):
    """4.2, 42 and 4,2 are one condition number."""
    return ".".join(re.findall(r"\d+", str(n or "")))


def heading_disputes(ca, cb):
    """Numbers one reader recorded and the other passed over as a heading.

    Only numbers that have children. A number with nothing beneath it that one
    reader missed is a lapse and the union covers it. A number with children is
    the case neither reader misread: one took it as binding on its own, the
    other as introducing the items below. The union silently keeps it, so
    without this the disagreement never reaches anybody.

    Returns (number, reader who recorded it, that reader's entry).
    """
    sides = {}
    for tag, side in (("1", ca), ("2", cb)):
        sides[tag] = {norm_number(c.get("number")): c for c in (side or [])
                      if states_a_requirement(c.get("text")) and norm_number(c.get("number"))}
    every = set(sides["1"]) | set(sides["2"])
    out = []
    for tag, other in (("1", "2"), ("2", "1")):
        for num, c in sides[tag].items():
            if num in sides[other]:
                continue
            if any(o != num and o.startswith(num + ".") for o in every):
                out.append((num, tag, c))
    return sorted(out, key=lambda r: [int(x) for x in r[0].split(".")])


def union_conditions(ca, cb, headings=None):
    """Every numbered requirement either reader found, at the finest numbering used.

    Numbered, and a requirement: an item answering "not applicable" is a number
    the form printed, not an obligation the authorization imposes. Dropping it
    here rather than asking each reader to drop it means the answer no longer
    depends on which reader was more literal — the union used to resolve the
    disagreement silently in favour of keeping them.
    """
    seen = {}
    for c in list(ca or []) + list(cb or []):
        key = norm_number(c.get("number"))
        if not key or not states_a_requirement(c.get("text")):
            continue
        if key not in seen:
            seen[key] = dict(c)
        elif len(str(c.get("text") or "")) > len(str(seen[key].get("text") or "")):
            seen[key].update(c)                            # keep the fuller text

    for num in headings or ():
        seen.pop(num, None)                            # settled: introduces its children

    folded = {k: fold(c.get("text")) for k, c in seen.items()}
    kept = []
    for key, c in seen.items():
        children = [k for k in folded if k != key and k.startswith(key + ".")]
        covered = "".join(folded[k] for k in children)
        if children and folded[key] and folded[key][:40] in covered:
            continue                                       # a parent its children carry
        kept.append(c)
    return sorted(kept, key=lambda c: [int(x) for x in norm_number(c["number"]).split(".")])
