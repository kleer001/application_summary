"""Segment the OCR sidecar into authorization documents and map them to spreadsheet rows."""
import re, sys, json

FILE_RX = re.compile(r"\b(\d{2})[-\s]?(H[A-Z]{3})[-\s]?([\dOolI]{5})\b")

TITLE_RX = re.compile(
    r"(paragraphs?)\s+3[45][^\n]{0,60}?fisheries\s+act\s*(?:authorization|\s)"
    r"|fisheries\s+act\s+authorization"
    r"|autorisation\s+aux\s+termes\s+des\s+alin[ée]as"
    r"|autorisation\s+vis[ée]{1,2}e?\s+.{0,14}?(?:paragraphes?|alin[ée]as?)"
    r"|autorisation[^\n]{0,40}loi\s+sur\s+les\s+p[êe]ches",
    re.I | re.S)

AUTHNO_RX = re.compile(r"N[\u00ba\u00b0o*]?\s*d[e\u2019' ]{0,4}(?:l\s*[\u2019'])?\s*autorisation\s*[:\-]", re.I)
AUTHNO_VAL_RX = re.compile(r"autorisation\s*[:\-]\s*(\d{4}\s*-\s*\d{2,3})", re.I)
CLOSING_RX = re.compile(
    r"Authorization\s+Limitations\s+and\s+Application\s+Conditions"
    r"|Limitations?\s+de\s+l[\u2019']autorisation"
    r"|Conditions\s+d[\u2019']application\s+et\s+limites"
    r"|Directeur\s+g[\u00e9e]n[\u00e9e]ral\s+r[\u00e9e]gional"
    r"|Regional\s+Director[- ]General", re.I)
ISSUED_RX = re.compile(r"authorization\s+issued\s+to"
                       r"|autorisation\s+(?:accord[ée]e|d[ée]livr[ée]e)", re.I)
LOC_RX = re.compile(r"location\s+of\s+proposed\s+project|description\s+of\s+proposed\s+project"
                    r"|emplacement\s+du\s+projet|description\s+du\s+projet", re.I)


def load_pages(path):
    return open(path, encoding="utf-8", errors="replace").read().split("\f")


def norm_file(m):
    digits = m[2].translate(str.maketrans("OolI", "0011"))
    return f"{m[0]}-{m[1]}-{digits}"


def find_starts(pages):
    """Pages that begin an authorization.

    Title lines are unreliable - OCR splits them ("AUTORISA TION", "AL INEAS") and
    the form has many wordings - so a start is identified structurally: an
    "issued to" line near the top, backed by a file-number or authorisation-number
    header, or a location / project-description section. Cover letters carry neither.
    """
    starts = []
    for i, p in enumerate(pages, 1):
        head = p[:900]
        if not ISSUED_RX.search(head):
            continue
        if not (FILE_RX.search(p[:400]) or AUTHNO_RX.search(p[:400]) or LOC_RX.search(p)):
            continue
        if starts and i - starts[-1] < 2 and not TITLE_RX.search(head):
            continue
        starts.append(i)
    return starts


def segment(pages):
    starts = find_starts(pages)
    segs = []
    for i, s in enumerate(starts):
        e = starts[i + 1] - 1 if i + 1 < len(starts) else len(pages)
        segs.append({"start": s, "end": e})
    for sg in segs:
        blob = pages[sg["start"] - 1:sg["end"]]
        # file number: prefer one repeated in page headers across the segment
        from collections import Counter
        hdr = Counter()
        anywhere = Counter()
        for p in blob:
            for m in FILE_RX.findall(p[:250]):
                hdr[norm_file(m)] += 1
            for m in set(FILE_RX.findall(p)):
                anywhere[norm_file(m)] += 1
        first_hdr = [norm_file(m) for m in FILE_RX.findall(blob[0][:400])] if blob else []
        # record whether the identifier needed OCR letter-for-digit repair
        sg["file_no_repaired"] = bool(first_hdr) and any(
            ch in m[2] for m in FILE_RX.findall(blob[0][:400]) for ch in "OolI") if blob else False
        an = AUTHNO_VAL_RX.search(blob[0][:600]) if blob else None
        sg["auth_no"] = re.sub(r"\s", "", an.group(1)) if an else None
        sg["file_no"] = (first_hdr[0] if first_hdr
                         else hdr.most_common(1)[0][0] if hdr
                         else anywhere.most_common(1)[0][0] if anywhere
                         else (f"Auth {sg['auth_no']}" if sg["auth_no"] else None))
        sg["hdr_votes"] = dict(hdr.most_common(3))
        # The authorization itself ends at whichever comes last: the final page
        # carrying its file-number stamp, or its closing/signature block. Anything
        # after that up to the next document is attached supporting material.
        last_stamped = last_closing = None
        for offset, p in enumerate(blob):
            page_no = sg["start"] + offset
            if sg["file_no"] and any(norm_file(m) == sg["file_no"]
                                     for m in FILE_RX.findall(p[:250])):
                last_stamped = page_no
            if CLOSING_RX.search(p):
                last_closing = page_no
        sg["package_end"] = sg["end"]
        doc_end = max([x for x in (last_stamped, last_closing) if x], default=None)
        if doc_end and doc_end < sg["end"]:
            sg["end"] = doc_end
            blob = pages[sg["start"] - 1:sg["end"]]
        sg["pages"] = sg["end"] - sg["start"] + 1
        # bates
        bates = []
        for p in blob:
            b = re.findall(r"\b(0{2}\d{4})\b", p)
            if b:
                bates.append(int(b[-1]))
        sg["bates_start"] = min(bates) if bates else None
        sg["bates_end"] = max(bates) if bates else None
    return segs


if __name__ == "__main__":
    pages = load_pages(sys.argv[1])
    segs = segment(pages)
    print(f"pages={len(pages)} segments={len(segs)}")
    nofile = [s for s in segs if not s["file_no"]]
    print("segments without a file number:", len(nofile), [s["start"] for s in nofile])
    from collections import Counter
    dup = [k for k, v in Counter(s["file_no"] for s in segs).items() if v > 1]
    print("file numbers spanning >1 segment:", dup)
    json.dump(segs, open(sys.argv[2], "w"), indent=1)
