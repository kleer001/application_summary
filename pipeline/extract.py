"""Extract structured fields from each authorization segment.

Works on whitespace-normalised segment text: OCR wraps headings across lines,
so line-anchored patterns miss most of them.
"""
import re

# OCR renders the superscript 2 of m2 as any of these
# OCR renders the superscript 2 of m2 as any of these, and the older
# authorization forms add straight and curly apostrophes.
SQ = r"m\s*[2²?7*°~^o'’‘´`\"]"
AREA = rf"(?:{SQ}|square\s+met(?:re|er)s|m[èeé]tres?\s+carr[ée]s?)"

SECT_RX = re.compile(
    r"(?:(\d{1,2})\s*[.,]\s*)?Conditions?\s+"
    r"(?:that\s+relate\s*(?:to|d\s+to)|relating\s+to"
    r"|(?:li[ée]es?|relatives?)\s+(?:aux?|[\u00e0a4]\s+l[ae]|[\u00e0a4]))\s+(.{0,140})",
    re.I)

CONTINGENCY_RX = re.compile(
    r"(?:(\d+\.\d+(?:\.\d+)?)\s+)?"
    r"(?:contingency\s+(?:measures?|plans?)|mesures?\s+(?:d[’']urgence|de\s+contingence))\s*:?",
    re.I)

DESTROY_RX = re.compile(rf"destruction\s+of\s+(?:up\s+to\s+)?([\d,\. ]+?)\s*{AREA}", re.I)
ALTER_RX = re.compile(rf"(?:permanent\s+)?alteration\s+of\s+(?:up\s+to\s+)?([\d,\. ]+?)\s*{AREA}", re.I)
DISRUPT_RX = re.compile(rf"disruption\s+of\s+(?:up\s+to\s+)?([\d,\. ]+?)\s*{AREA}", re.I)
MEASURE_RX = re.compile(rf"([\d][\d,\. ]{{0,14}}?)\s*{AREA}", re.I)
HA_RX = re.compile(r"([\d][\d,\.]{0,10})\s*(?:ha\b|hectares?)", re.I)
LINEAR_RX = re.compile(r"([\d][\d,\.]{0,10})\s*(?:linear\s+met(?:re|er)s|m[èe]tres?\s+lin[ée]aires?)", re.I)

DATE_TXT_RX = re.compile(
    r"\b(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|SEPT|OCT|NOV|DEC)[A-Za-z]*\.?\s+(\d{1,2})[,.]?\s+(20\d{2})\b", re.I)
DATE_DMY_RX = re.compile(
    r"\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(20\d{2})\b", re.I)
ISO_RX = re.compile(r"\b(20\d{2})[-/](\d{2})[-/](\d{2})\b")

MONTHS = dict(jan="01", feb="02", mar="03", apr="04", may="05", jun="06", jul="07",
              aug="08", sep="09", sept="09", oct="10", nov="11", dec="12",
              january="01", february="02", march="03", april="04", june="06",
              july="07", august="08", september="09", october="10",
              november="11", december="12")


def normalise(s):
    return re.sub(r"\s+", " ", s).strip()


def seg_text(pages, sg):
    return normalise("\n".join(pages[sg["start"] - 1: sg["end"]]))


def clean(s, cap=1800):
    return normalise(s).strip(" .,;:-")[:cap]


def num(s):
    if s is None:
        return None
    s = re.sub(r"[^\d\.]", "", s.replace(" ", ""))
    s = re.sub(r"\.(?=\d{3}\b)", "", s)          # 1.090 thousands-separator
    if not s or s.count(".") > 1:
        return None
    try:
        v = float(s)
    except ValueError:
        return None
    return v if v > 0 else None


def sections(text):
    """Ordered list of (number, title, body) for 'Conditions that relate to X' headings.

    The section number is often lost or garbled by OCR, so headings are found by
    phrase and bodies are sliced between consecutive headings.
    """
    marks = [(m.start(), m.group(1), m.group(2)) for m in SECT_RX.finditer(text)]
    out = []
    for i, (pos, n, title) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        title = re.split(r"\s\d+\.\d|:", title)[0].strip(" .,;:-")
        out.append((n, title, text[pos:end]))
    return out


def _next_non_child(text, number, start):
    """Offset of the next numbered item that is not a child of `number`."""
    for m in re.finditer(r"(?<![\d.])(\d+\.\d+(?:\.\d+)?)\s+[A-ZÀ-Ü(]", text[start:]):
        cand = m.group(1)
        if cand == number or cand.startswith(number + "."):
            continue
        return start + m.start()
    return None


def find_contingency(text):
    for m in CONTINGENCY_RX.finditer(text):
        number = m.group(1)
        body_start = m.end()
        if number:
            end = _next_non_child(text, number, body_start)
        else:
            nm = re.search(r"(?<![\d.])\d+\.\d+\s+[A-ZÀ-Ü(]", text[body_start:])
            end = body_start + nm.start() if nm else None
        body = text[body_start: end if end else body_start + 1200]
        if len(body.strip()) >= 40:
            return clean(body)
    return None


def hadd_figures(text):
    def one(rx):
        m = rx.search(text)
        return num(m.group(1)) if m else None
    return one(DESTROY_RX), one(ALTER_RX), one(DISRUPT_RX)


def measures(text):
    """Deduped area figures, largest first, as (value, unit)."""
    out = {}
    for rx, unit in ((MEASURE_RX, "m2"), (HA_RX, "ha"), (LINEAR_RX, "linear m")):
        for m in rx.finditer(text):
            v = num(m.group(1))
            if v and v >= 1:
                out.setdefault((v, unit), None)
    return sorted(out, key=lambda t: -t[0])


def find_date(text):
    for rx, order in ((ISO_RX, "ymd"), (DATE_TXT_RX, "mdy"), (DATE_DMY_RX, "dmy")):
        m = rx.search(text)
        if not m:
            continue
        if order == "ymd":
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        if order == "mdy":
            return f"{m.group(3)}-{MONTHS[m.group(1).lower()]}-{int(m.group(2)):02d}"
        return f"{m.group(3)}-{MONTHS[m.group(2).lower()]}-{int(m.group(1)):02d}"
    return None



IMPACT_RX = re.compile(
    r"(?:are\s+likely\s+to\s+result\s+in\s+the\s+following\s+impacts?\s+to\s+fish\s+and\s+fish\s+habitat\s*:"
    r"|serious\s+harm\s+to\s+fish\s+likely\s+to\s+result\s+from\s+the\s+proposed[^:]{0,120}?(?:are|is)\s*:?"
    r"|sont\s+susceptibles?\s+d[’\']entra[îi]ner\s+les\s+effets\s+suivants[^:]{0,40}:)",
    re.I)

TOTAL_RX = re.compile(
    rf"total\s+area\s+of\s+impact\s+to\s+fish\s+habitat\s+is\s+(?:approximately\s+)?([\d][\d,\. ]{{0,12}}?)\s*{AREA}",
    re.I)


def find_impact_summary(text):
    m = IMPACT_RX.search(text)
    if not m:
        return None
    tail = text[m.end():]
    stop = re.search(r"Conditions?\s+of\s+Authorization|Conditions?\s+that\s+relate\s+to"
                     r"|\bPARAGRAPHS?\s+3[45]|\bPATH\s+No|\b0{2}\d{4}\b|Canada\s+0{2}\d{4}", tail, re.I)
    body = tail[:stop.start()] if stop else tail[:1200]
    return clean(body) or None


def find_total_impact(text):
    m = TOTAL_RX.search(text)
    return num(m.group(1)) if m else None



# Impact bullets list components ("Destruction of 4,196 m2 ...; Destruction of
# 1,266 m2 ...") that must be summed, so figures are totalled within one block.
COMP_RX = {
    "destruction": re.compile(rf"destruction\s+of\s+(?:up\s+to\s+|approximately\s+)?([\d][\d,\. ]{{0,12}}?)\s*{AREA}", re.I),
    "alteration": re.compile(rf"alteration(?:\s*,?\s*disruption)?\s+of\s+(?:up\s+to\s+|approximately\s+)?([\d][\d,\. ]{{0,12}}?)\s*{AREA}", re.I),
    "disruption": re.compile(rf"disruption\s+of\s+(?:up\s+to\s+|approximately\s+)?([\d][\d,\. ]{{0,12}}?)\s*{AREA}", re.I),
}

# "217 m2 of intertidal rocky habitat and 328 m2 of subtidal rocky habitat"
AND_RX = re.compile(rf"\band\s+([\d][\d,\. ]{{0,12}}?)\s*{AREA}", re.I)


def hadd_from_block(block):
    """Sum each impact type across the components listed in one impact block."""
    if not block:
        return {}, {}
    out, parts = {}, {}
    for kind, rx in COMP_RX.items():
        vals = []
        for m in rx.finditer(block):
            v = num(m.group(1))
            if not v:
                continue
            vals.append(v)
            tail = block[m.end():m.end() + 90]
            am = AND_RX.match(tail.lstrip()) or AND_RX.search(tail[:60])
            if am:
                av = num(am.group(1))
                if av:
                    vals.append(av)
        vals = _drop_stated_total(_dedupe_restatement(vals))
        if vals:
            out[kind] = round(sum(vals), 1)
            parts[kind] = vals
    return out, parts


def _dedupe_restatement(vals):
    """Authorizations often restate the impact list verbatim; halve an exact repeat."""
    n = len(vals)
    if n >= 2 and n % 2 == 0 and vals[:n // 2] == vals[n // 2:]:
        return vals[:n // 2]
    return vals


def _drop_stated_total(vals):
    """A figure equal to the sum of the others is a stated total, not a component.

    Tried and rejected: dropping any figure whose removal leaves a sum that appears
    elsewhere in the clause. Impact blocks carry many numbers, so that rule stripped
    real components and measured worse against known-good values.
    """
    if len(vals) < 3:
        return vals
    total = sum(vals)
    for i, v in enumerate(vals):
        if abs((total - v) - v) <= max(1.0, v * 0.01):
            return vals[:i] + vals[i + 1:]
    return vals


def extract(pages, sg):
    text = seg_text(pages, sg)
    sects = sections(text)
    off = mon = None
    for n, title, body in sects:
        low = title.lower()
        has_off = bool(re.search(r"offsett?ing|compensation", low))
        has_mon = "monitoring and reporting" in low
        if off is None and has_off and not has_mon:
            off = body
        if mon is None and has_mon and not has_off:
            mon = body
    impact = find_impact_summary(text[:12000])
    summed, parts = hadd_from_block(impact)
    d, a, di = hadd_figures(text[:9000])
    return {
        "file_no": sg["file_no"],
        "page_start": sg["start"], "page_end": sg["end"],
        "bates_start": sg.get("bates_start"), "bates_end": sg.get("bates_end"),
        "contingency": find_contingency(text),
        "monitoring": clean(mon) if mon else None,
        "offsetting": clean(off) if off else None,
        "offset_measures": measures(off)[:8] if off else [],
        "hadd_destruction": d, "hadd_alteration": a, "hadd_disruption": di,
        "impact_summary": impact,
        "hadd_sum": summed,
        "hadd_parts": parts,
        "total_impact_m2": find_total_impact(text),
        "date": find_date(text[:3000]),
        "n_sections": len(sects),
    }


# ---- front-matter fields (present on the first page of every authorization) --
FRONT = {
    # Names sit on the line after the label, so these are multiline+dotall and
    # stop at the first line break.
    "proponent": re.compile(
        r"(?:Authorization\s+issued\s+to"
        r"|Autorisation\s+(?:accord[\u00e9e]e|d[\u00e9e]livr[\u00e9e]e)\s*[\u00e0a4]?)"
        r"\s*[:\-]?\s*(.{3,140}?)\s*(?:\(hereafter|\(ci-apr[\u00e8e]s|$)",
        re.I | re.S | re.M),
    "auth_number": re.compile(
        r"N[\u00ba\u00b0o*]?\s*d\s*[\u2019'\u2018]?\s*autorisation\s*[:\-]\s*(\d{4}\s*-\s*\d{2,3})", re.I),
    "province": re.compile(r"Province\s*[:\-]\s*([A-Za-z\u00c0-\u00ff' \-]{3,40})", re.I),
    "community": re.compile(
        r"Nearest\s+community[^:]{0,40}:\s*([^\n]{2,60})"
        r"|collectivit[\u00e9e]\s+la\s+plus\s+proche[^:]{0,40}:\s*([^\n]{2,60})", re.I),
    "waterbody": re.compile(
        r"Name\s+of\s+watercourse,?\s+waterbody\s*[:\-]\s*([^\n]{2,80})"
        r"|(?:cours\s+d[\u2019'\s]*eau\s+ou\s+du\s+)?plan\s+d[\u2019'\s]*eau\s*[:\-]\s*([^\n]{2,80})", re.I),
    "project": re.compile(
        r"(?:Description\s+of\s+Proposed\s+Project|Description\s+du\s+projet\s+propos[\u00e9e])[^:]{0,90}:?\s*"
        r"(?:The\s+proposed\s+project[^:]{0,90}:|Le\s+projet\s+propos[\u00e9e][^:]{0,120}:)?\s*(.{40,700})",
        re.I | re.S),
}


def front_fields(pages, sg):
    """Fields from the authorization's first page, before whitespace collapsing."""
    head = "\n".join(pages[sg["start"] - 1: min(sg["end"], sg["start"] + 1)])
    out = {}
    for k, rx in FRONT.items():
        m = rx.search(head)
        if not m:
            out[k] = None
            continue
        val = next((g for g in m.groups() if g), "")
        val = clean(val, 700 if k == "project" else 120)
        if k == "proponent":
            # the older form labels the field: "Authorization issued to: Name: Acme Ltd"
            val = re.sub(r"^Name\s*[:\-]\s*", "", val, flags=re.I)
        if k == "project":
            # the lead-in sentence often ends mid-word after OCR ("...tie comprend :")
            lead = val[:45]
            if ":" in lead:
                val = val[lead.rindex(":") + 1:].strip()
        out[k] = val or None
    return out
