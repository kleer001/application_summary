"""Folding OCR noise away, in one place because it must be one rule.

Verification, combination and comparison all decide whether two pieces of text
say the same thing. If they ever fold differently, a value passes one check under
one rule and is judged under another, and nothing reports it. This module is the
rule.
"""
import re

# m2 renders every one of these ways in the scan. The letter variant is matched
# only outside a word, or "monitoring" folds to "m2nitoring" and "confirm
# offsetting" to "confirmoffsetting" with the m and the o eaten. The double
# quotes are the superscript 2 read as a ditto mark, observed as "2 m" and
# "3.3 km" in this release.
SQ = r"m\s*[2²?7*°~^’'”\"″]|m\s*o(?![a-z])"


# A date's ordinal suffix is set in superscript, and the scanner reads the
# superscript as punctuation: "April 1st" becomes "April 1%", "June 30th"
# becomes "June 30\"". Dropping the suffix makes the two renderings agree, and
# loses nothing — the digits carry the date.
ORD = r"(?<=\d)(st|nd|rd|th)\b"


def norm(s):
    """Letters and digits only, with m2 spellings and date ordinals collapsed.

    Numeric fidelity is deliberately not preserved here; verify.digits_present
    checks that separately against the unfolded quote.
    """
    s = re.sub(SQ, " m2 ", str(s).lower())
    s = re.sub(ORD, "", s)
    return re.sub(r"[^a-z0-9]+", "", s)


def wordset(s):
    """The words of a value, folded by the rules `norm` already applies.

    `norm` collapses a value to a single string. That preserves character order,
    which is what containment needs, but it cannot see two readers naming the
    same things in a different order, or one writing a figure with its unit and
    the other without: "650 m2 180 m2" and "180 650" fold to strings that share
    no prefix. This is the same fold stopping at word boundaries instead of
    erasing them, so the two rules cannot disagree about m2 spellings or date
    ordinals — the damage a second, independent fold would reintroduce.

    A trailing "s" is dropped from words longer than three characters, because
    "Paragraph" against "Paragraphs" and "measure" against "measures" are the
    same word and the plural is the writer's, not the document's.
    """
    s = re.sub(SQ, " m2 ", str(s).lower())
    s = re.sub(ORD, "", s)
    out = set()
    for w in re.findall(r"[a-z0-9]+", s):
        out.add(w[:-1] if len(w) > 3 and w.endswith("s") else w)
    return out


def tokens(s):
    """Words of three or more characters, which is what survives OCR intact."""
    return [t for t in re.findall(r"[a-z0-9]+", str(s).lower()) if len(t) > 2]


def on_page(quote, page_folded, page_tokens, threshold=0.9):
    """Is this quote text from this page?

    Exact containment after folding is the strong answer. Where that fails, the
    question is whether the OCR rendered the same words differently, or whether
    the reader wrote something the page does not say. The contract tells readers
    to prefer the scan where the text layer is mangled, so demanding the text
    layer render a quote character for character makes the OCR the authority over
    the page it is a lossy copy of.

    Measured on the first wave: of the quotes exact matching rejected, those the
    reader had genuinely read off the page carried every one of their words on it,
    while reconstructions carried about half. The gap is wide and this threshold
    sits in it.
    """
    if norm(quote) in page_folded:
        return "exact"
    qt = tokens(quote)
    if not qt:
        return None
    hit = sum(1 for t in qt if t in page_tokens)
    return "ocr" if hit / len(qt) >= threshold else None
