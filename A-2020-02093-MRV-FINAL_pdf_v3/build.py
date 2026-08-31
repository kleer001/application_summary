"""Assemble the workbook from verified reader output.

One row per authorization — usually one per file number, and one per number a
letter grants where it grants several. Every text cell is a verbatim quote and
every row cites the pages it came from, so any value can be checked against the page that carries
it. Nothing is copied from the prior summary; cells this run cannot support are
left empty and the reason is on the Review_Queue.
"""
import functools, json, os, re, sys
from collections import Counter, defaultdict

from combine import combine_field, heading_disputes, union_conditions
from ids import corrected, file_no_of, stem_of
from norm import norm
from paths import complete_stems
from verify import VERIFIED, check_conditions, check_field, load_pages, verdicts_for

HERE = os.path.dirname(os.path.abspath(__file__))

# The prior summary's 30 columns, in its order, each naming what fills it.
# A field name reads that field; "@" runs the derivation of that name below;
# "-" is a column no page can answer.
#
# The three marked "-" are not extraction failures. `Source_Part` and
# `Source_File` name which file of the split release a copy arrived in, which is
# a fact about delivery and is printed on no page. `Review_Notes` is where a
# reviewer writes. Nothing in the release can fill any of them.
PRIOR = [
    ("Source_Part", "-"), ("Source_File", "-"),
    ("DFO_File_or_PATH", "file_number"),
    ("Authorization_Date", "date_of_issuance"),
    ("Authorization_Issue_Year", "@issue_year"),
    ("Amendment_Date", "@amendment_date"), ("Amendment_Year", "@amendment_year"),
    ("Proponent", "proponent"),
    ("Project_Name_or_Description", "project_description"),
    ("Province", "province"),
    ("Aquatic_Setting", "@setting"), ("Project_Type", "@project_type"),
    ("Authorized_Impact_Summary", "@impact_summary"),
    ("HADD_Destruction_m2", "hadd_destruction_m2"),
    ("HADD_Alteration_m2", "hadd_alteration_m2"),
    ("HADD_Disturbance_m2", "hadd_disturbance_m2"),
    ("HADD_Total_m2", "total_impact_area_m2"),
    ("HADD_Other_Units", "impact_other_units"),
    ("Total_Habitat_Affected_m2", "project_footprint_area_m2"),
    ("Offsetting_Measures", "offsetting_measures"),
    ("Offsetting_Required", "offsetting_required_amount"),
    ("Offsetting_Provided", "offsetting_provided_amount"),
    ("Offsetting_Unit", "@offsetting_unit"),
    ("Habitat_Bank_Name", "habitat_bank_name"),
    ("Monitoring_Requirements", "@monitoring"),
    ("Contingency_Measures", "@contingency"),
    ("Include_in_2021_Request", "@include_2021"),
    ("QA_Flag", "@qa_flag"), ("Review_Notes", "-"),
    ("Source_Reference_ID", "@page_anchor"),
]


def abs_page(page, first):
    """Readers cite pages numbered from 1; the workbook cites the release."""
    return page + first - 1 if isinstance(page, int) else None


def cell(entries):
    """Entries to one cell: a stated total if there is one, else all of them."""
    if not entries:
        return None
    total = [e for e in entries if e.get("role") == "total"]
    if total:
        return total[0]["value"]
    if len(entries) == 1:
        return entries[0]["value"]
    # One value said twice is one value. A reader that quotes the same figure
    # from two places returns two entries, and joining them produced cells like
    # "17-HQUE-00044; 17-HQUE-00044" — which for the column that keys the row
    # meant the row could not be found by its own file number. Sameness is
    # folded, as it is everywhere else here: "65 m2" and "65 m²" are one value,
    # and raw string equality would let the same cell back in.
    seen, out = set(), []
    for e in entries:
        v = str(e["value"])
        if norm(v) not in seen:
            seen.add(norm(v))
            out.append(v)
    return "; ".join(out)


def absolutise(doc, first):
    """Rewrite every cited page to a release page, once, here.

    Downstream nothing needs to know a document's offset, so no later caller can
    apply it twice or apply the wrong document's.
    """
    for f in doc.get("fields", {}).values():
        for e in (f or {}).get("entries") or []:
            if isinstance(e, dict):
                e["page"] = abs_page(e.get("page"), first)
    for c in doc.get("conditions", []) or []:
        c["page"] = abs_page(c.get("page"), first)


def labels(sandbox):
    """Pass D output, keyed by file number then vocabulary.

    A label is reasoned from an extracted value rather than quoted from a page,
    so it is written with the project's marker for exactly that and names the
    field it was reasoned from.
    """
    out, d = {}, f"{sandbox}/labelled"
    if not os.path.isdir(d):
        return out
    for f in sorted(os.listdir(d)):
        blocks = json.load(open(f"{d}/{f}"))
        for b in (blocks if isinstance(blocks, list) else [blocks]):
            for l in b["labels"]:
                terms = l.get("terms") or []
                if terms:
                    out.setdefault(l["file_number"], {})[b["vocabulary"]] = terms
    return out


@functools.lru_cache(maxsize=4)
def _rulings(sandbox):
    """Every ruling on disk, by stem. One listing, not one per document."""
    out = {}
    d = f"{sandbox}/adjudicated"
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            if f.endswith(".json"):
                a = json.load(open(f"{d}/{f}"))
                out.setdefault(f.split(".")[0], {})[a["field"]] = a
    return out


def adjudications(sandbox, doc_id):
    """Pass C answers already on disk for this document, keyed by field."""
    return _rulings(sandbox).get(stem_of(doc_id), {})


def read_document(order, queue):
    """One document: two readers for the fields, two more for the conditions.

    The two passes are read separately and are combined by different rules —
    agreement for a bounded field, union for an enumeration — so they are loaded
    separately here rather than pulled out of one file.
    """
    out_dir = os.path.dirname(order["out"])

    def load(tag):
        path = os.path.join(out_dir, f"{order['stem']}.{tag}.json")
        if os.path.exists(path):
            return json.load(open(path))
        queue.append({"document": order["doc_id"], "field": "*",
                      "why": f"reader {tag} wrote no file", "resolved": False,
                      "reason": "no_file"})
        return {"fields": {}, "conditions": []}

    fields_docs = {t: load(f"a{t}") for t in ("1", "2")}
    cond_docs = {t: load(f"b{t}") for t in ("1", "2")}

    # Verify while the pages are still the ones the reader cited. Absolutising
    # first puts every page outside the document's own 1..N range and rejects
    # the lot.
    checked = {t: verdicts_for(d, order["slice"], order["first_page"], order["last_page"])
               for t, d in fields_docs.items()}
    cond_verdicts = {t: {num: v for num, v, _ in check_conditions(d, order["slice"])}
                     for t, d in cond_docs.items()}
    for d in list(fields_docs.values()) + list(cond_docs.values()):
        absolutise(d, order["first_page"])
    ruled = adjudications(os.path.dirname(os.path.dirname(order["out"])), order["doc_id"])
    fields = {}
    names = set(fields_docs["1"].get("fields", {})) | set(fields_docs["2"].get("fields", {}))
    for name in sorted(names):
        entries, note, resolved, reason = combine_field(
                                                fields_docs["1"].get("fields", {}).get(name),
                                                fields_docs["2"].get("fields", {}).get(name),
                                                checked["1"].get(name, "missing"),
                                                checked["2"].get(name, "missing"))
        if not resolved and name in ruled:
            a = ruled[name]
            if a.get("winner") == "absent":
                # The adjudicator read the pages and the field is not on them.
                # That is an answer: the cell is empty because the document is
                # silent, which is different from empty because nobody could
                # verify a quote, and only one of the two is settled.
                entries, resolved, reason = [], True, "passc_settled"
                note = f'pass C (absent): {a.get("reason", "")[:110]}'
            elif a.get("winner") != "unresolved" and a.get("entries"):
                # An adjudicated answer is checked exactly as a reader's is. The
                # adjudicator is a better reader, not an exempt one, and a cell
                # it certifies has to be findable on the page it cites.
                verdict = check_field(name, {"entries": a["entries"]},
                                      load_pages(order["slice"]),
                                      order["last_page"] - order["first_page"] + 1)[1]
                if verdict in VERIFIED:
                    # Pass C cites pages from 1, as a reader does; these arrive
                    # after the reader output was absolutised, so they need it too.
                    entries = [dict(e, page=abs_page(e.get("page"), order["first_page"]))
                               for e in a["entries"]]
                    resolved = True
                    reason = "passc_settled"
                    note = f'pass C ({a["winner"]}): {a.get("reason", "")[:110]}'
                    if verdict == "QUEUE":
                        note += " [read from the scan, not the text layer]"
                else:
                    reason = "passc_failed_check"
                    note = (f'pass C answer failed its own check ({verdict}); '
                            f'the conflict stands')
            else:
                reason = "passc_unsettled"
                note = f'pass C could not settle it: {a.get("reason", "")[:120]}'
        if note:
            queue.append({"document": order["doc_id"], "field": name, "why": note,
                          "resolved": resolved, "reason": reason})
        fields[name] = entries

    kept = []
    for t, d in cond_docs.items():
        verdicts = cond_verdicts[t]
        def ruled_absent(c):
            r = ruled.get(f"condition {c.get('number')}")
            return bool(r) and r.get("winner") == "absent"

        kept.append([c for c in d.get("conditions", []) or []
                     if not ruled_absent(c)
                     and (verdicts.get(c.get("number")) in VERIFIED
                          or f"condition {c.get('number')}" in ruled)])
        for c in d.get("conditions", []) or []:
            v = verdicts.get(c.get("number"))
            if v == "pass":
                continue
            name = f"condition {c.get('number')}"
            ruling = ruled.get(name)
            if v != "QUEUE" and ruling and ruling.get("entries"):
                # Pass C found the condition and certified its text; the reader's
                # copy was defeated by the OCR, not by the document.
                e = ruling["entries"][0]
                c["text"] = e.get("value", c.get("text"))
                c["page"] = abs_page(e.get("page"), order["first_page"]) or c.get("page")
                c["source"] = e.get("source", "image")
                queue.append({
                    "document": order["doc_id"], "field": name,
                    "why": f'pass C located it: {ruling.get("reason", "")[:110]}',
                    "resolved": True, "reason": "condition_located"})
                continue
            if ruling and ruling.get("winner") == "absent":
                # Read against the scan, the number carries no condition. It is
                # dropped from the sheet rather than left in it uncheckable.
                queue.append({
                    "document": order["doc_id"], "field": name,
                    "why": f'pass C found nothing there: {ruling.get("reason", "")[:100]}',
                    "resolved": True, "reason": "condition_absent"})
                continue
            queue.append({
                "document": order["doc_id"], "field": name,
                "why": ("may be cut off at a page break - check it is whole"
                        if v == "QUEUE" else "text does not appear on the page it cites"),
                "resolved": False,
                "reason": "condition_page_break" if v == "QUEUE" else "condition_off_page"})

    # A number one reader recorded and the other read as a heading. The union
    # keeps it either way, so unless it is queued here nobody is ever asked.
    headings = set()
    for num, tag in heading_disputes(*kept):
        ruling = ruled.get(f"heading {num}")
        verdict = (ruling or {}).get("winner")
        settled = verdict in ("heading", "condition")
        if verdict == "heading":
            headings.add(num)
        queue.append({
            "document": order["doc_id"], "field": f"heading {num}", "number": num,
            "why": (f'pass C: {num} is a {verdict} — {(ruling.get("reason") or "")[:100]}'
                    if settled else
                    f"reader {tag} recorded {num} as a condition; the other read it "
                    f"as a heading introducing the numbers beneath it"),
            "resolved": settled,
            "reason": "heading_settled" if settled else "heading_dispute"})

    return {"doc_id": order["doc_id"],
            "file_number": corrected(order["stem"], order["file_number"]),
            "first": order["first_page"], "last": order["last_page"],
            "language": order["language"], "fields": fields,
            "conditions": union_conditions(*kept, headings=headings)}


def merge_documents(docs, discrepancies):
    """Several documents under one file number become one row.

    The amendment is the document that says it amends something; failing that,
    the later date of issuance. The row shows what is authorized now and the
    superseded figure is kept on Discrepancies rather than dropped.
    """
    def issue(d):
        e = d["fields"].get("date_of_issuance") or []
        return str(e[0]["value"]) if e else ""

    def amends(d):
        e = d["fields"].get("related_authorizations") or []
        return any("amend" in str(x.get("value", "")).lower() for x in e)

    ordered = sorted(docs, key=lambda d: (amends(d), issue(d), d["first"]))
    merged = {"documents": ordered, "fields": {}, "conditions": []}
    for d in ordered:
        for name, entries in d["fields"].items():
            if not entries:
                continue
            prior = merged["fields"].get(name)
            if prior and cell(prior) != cell(entries):
                discrepancies.append({
                    "file_number": d["file_number"], "field": name,
                    "earlier": cell(prior),
                    "earlier_pages": [e.get("page") for e in prior],
                    "later": cell(entries),
                    "later_pages": [e.get("page") for e in entries],
                })
            merged["fields"][name] = entries
        merged["conditions"] += [dict(c, document=d["doc_id"]) for c in d["conditions"]]
    return merged


# ---------------------------------------------------------------- derivations
# A column nobody asks a reader for. Each takes the merged row and the review
# queue bucketed by file number, and returns one cell value.
#
# Values reasoned from the text rather than quoted from it carry a trailing (i),
# which is the project's marker for exactly that. A cell without it is a quote.
INFERRED = " (i)"


def _issue_date(row):
    e = row["fields"].get("date_of_issuance") or []
    return str(e[0]["value"]) if e else None


def _amendment_dates(row):
    out = []
    for d in row["documents"][1:]:
        e = d["fields"].get("date_of_issuance") or []
        if e:
            out.append(str(e[0]["value"]))
    return out


def _qa_flag(row, queue_by_fn, *_):
    flags = []
    if not any(row["fields"].get(n) for n in
               ("hadd_destruction_m2", "hadd_alteration_m2", "total_impact_area_m2")):
        flags.append("no impact area extracted")
    if len(row["documents"]) > 1:
        flags.append(f"{len(row['documents'])} documents merged")
    flags += sorted({q["field"] for q in queue_by_fn.get(row["documents"][0]["file_number"], [])
                     if not q["resolved"]})
    return "; ".join(flags) or None


def _monitoring(row, *_):
    parts = [cell(row["fields"].get("monitoring_duration") or []),
             cell(row["fields"].get("monitoring_frequency") or [])]
    got = [c for c in row["conditions"] if c.get("topic") in ("monitoring", "reporting")]
    if got:
        parts.append(f"{len(got)} monitoring or reporting conditions")
    parts = [str(p) for p in parts if p]
    return "; ".join(parts) + INFERRED if parts else None


def _impact_summary(row, *_):
    bits = [cell(row["fields"].get("project_description") or [])]
    for name, word in (("hadd_destruction_m2", "destruction"),
                       ("hadd_alteration_m2", "alteration"),
                       ("hadd_disturbance_m2", "disturbance")):
        v = cell(row["fields"].get(name) or [])
        if v is not None:
            bits.append(f"{word} {v} m2")
    bits = [str(b) for b in bits if b]
    return "; ".join(bits) + INFERRED if bits else None


def _offsetting_unit(row, *_):
    text = " ".join(str(cell(row["fields"].get(n) or [])) for n in
                    ("offsetting_required_amount", "offsetting_provided_amount"))
    units = {u.replace("²", "2") for u in
             re.findall(r"\b(m2|m²|ha|hectares?|km|m linéaires?|linear m(?:etres)?)\b", text)}
    return "; ".join(sorted(units)) + INFERRED if units else None


def _page_anchor(row, *_):
    pages = [e.get("page") for f in row["fields"].values() for e in f
             if isinstance(e.get("page"), int)]
    return f"pp. {min(pages)}-{max(pages)}" if pages else None


def _setting(row, _, labels):
    return label_cell(labels.get("setting"))


def _project_type(row, _, labels):
    """The prior column reads "activity / sector"; both halves are labels."""
    act, sec = labels.get("activity"), labels.get("sector")
    if not act and not sec:
        return None
    left = "; ".join(act) if act else ""
    right = "; ".join(sec) if sec else ""
    return (f"{left} / {right}" if left and right else left or right) + INFERRED


DERIVED = {
    "@setting": _setting,
    "@project_type": _project_type,
    "@issue_year": lambda row, *_: (_issue_date(row) or "")[:4] or None,
    "@amendment_date": lambda row, *_: "; ".join(_amendment_dates(row)) or None,
    "@amendment_year": lambda row, *_: "; ".join(sorted({d[:4] for d in _amendment_dates(row)})) or None,
    # Yes exactly when the authorization issued in 2021. All 96 decided rows of
    # the prior summary follow this rule and none contradict it; where no issue
    # date was extracted the rule has no input and the cell stays empty.
    "@include_2021": lambda row, *_: (None if not _issue_date(row)
                                      else ("Yes" if _issue_date(row).startswith("2021") else "No")),
    "@contingency": lambda row, *_: (
        f"{len([c for c in row['conditions'] if c.get('topic') == 'contingency'])} "
        f"on the Conditions sheet" + INFERRED
        if any(c.get("topic") == "contingency" for c in row["conditions"]) else None),
    "@monitoring": _monitoring,
    "@impact_summary": _impact_summary,
    "@offsetting_unit": _offsetting_unit,
    "@page_anchor": _page_anchor,
    "@qa_flag": _qa_flag,
}

# Vocabularies that get a column of their own. The workbook reproduces the prior
# summary's layout, and that layout has no column for a controlled term, so this
# is empty: a label reaches the sheet only through `Aquatic_Setting` and
# `Project_Type`, which the prior summary does have and which `_setting` and
# `_project_type` derive from the setting, activity and sector labels.
VOCABULARIES = []


def label_cell(terms):
    return "; ".join(terms) + INFERRED if terms else None


def derive(row, key, queue_by_fn, row_labels):
    if key not in DERIVED:
        raise KeyError(f"{key} appears in PRIOR but nothing derives it")
    return DERIVED[key](row, queue_by_fn, row_labels)


def split_by_authorization(row):
    """One row per authorization, where a letter grants more than one.

    A single letter can grant several numbered authorizations at once, and where
    it does it says under its own headings which impacts belong to which. One row
    holding all of them is a record of no authorization: its area cells carry
    figures from several separate regulatory decisions with nothing to say which
    decision each belongs to, and a reader of the sheet cannot recover it.

    A field whose entries carry no attribution is stated once for the whole
    letter — the proponent, the project, the dates — and is repeated on each row
    unchanged. An entry left unattributed in a field where others were attributed
    is repeated too, rather than dropped: the reader did not say where it goes,
    and showing it on every row states that plainly where discarding it would
    hide it.

    What triggers the split is the **attribution**, not how many numbers the
    letter prints. A letter naming several and sorting nothing under them — an
    amendment citing the authorization it amends, a form carrying a related file
    number — grants one authorization, and splitting it would turn one honest
    pooled row into several rows each falsely claiming all of the figures.
    """
    # Folded to compare, kept as printed to write: the fold exists to match
    # identifiers through OCR damage, never to put one in a cell.
    filed = {}
    for entries in row["fields"].values():
        for e in entries:
            if e.get("authorization"):
                filed.setdefault(norm(e["authorization"]), e["authorization"])
    if len(filed) < 2:
        return [row]
    out = []
    for where, printed in filed.items():
        fields = {}
        for name, entries in row["fields"].items():
            if name == "file_number":
                fields[name] = [e for e in entries if norm(e.get("value")) == where]
            else:
                fields[name] = [e for e in entries
                                if not e.get("authorization")
                                or norm(e["authorization"]) == where]
        out.append({**row, "fields": fields, "authorization": printed})
    return out


def row_key(row):
    """What the row is filed under. Its own authorization where it has one."""
    return row.get("authorization") or row["documents"][0]["file_number"]


def by_document(rows):
    """The rows, one per set of documents.

    Several rows can share one document, because a letter granting several
    authorizations produces a row for each. Anything counted or written per
    document rather than per row has to come through here, or a count the
    document states once is reported several times.
    """
    return list({tuple(d["doc_id"] for d in r["documents"]): r
                 for r in rows}.values())


# ------------------------------------------------------------------- assembly
def assemble(sandbox):
    """Every document whose four reads are present. A wave is built from what it
    finished, not from what it was asked to do, so a partial wave still builds."""
    orders = json.load(open(f"{sandbox}/wave.json"))
    complete = complete_stems(sandbox)
    orders = [o for o in orders if o["stem"] in complete]
    queue, discrepancies = [], []
    seen = set()
    docs = []
    for o in orders:
        if o["stem"] in seen:
            continue
        seen.add(o["stem"])
        docs.append(read_document(o, queue))
    for q in queue:
        # The queue is read by file number, so it has to move with the row.
        q["file_number"] = corrected(stem_of(q["document"]), file_no_of(q["document"]))

    by_fn = defaultdict(list)
    for d in docs:
        by_fn[d["file_number"]].append(d)
    rows = sorted((r for v in by_fn.values()
                   for r in split_by_authorization(merge_documents(v, discrepancies))),
                  key=row_key)
    return rows, docs, queue, discrepancies


def write_workbook(rows, docs, queue, discrepancies, spec, out_path, labelled=None):
    # Imported here rather than at the top so that finding conflicts, which is
    # the front half of this module and needs no spreadsheet, runs on the
    # standard library alone. A reading night has no openpyxl and does not
    # need one to hand its disagreements to an adjudicator.
    import openpyxl
    from openpyxl.styles import Font

    labelled = labelled or {}
    docrows = by_document(rows)
    used = {src for _, src in PRIOR if not src.startswith(("@", "-"))}
    extended = [n for n in spec if n not in used]
    queue_by_fn = defaultdict(list)
    for q in queue:
        queue_by_fn[q["file_number"]].append(q)

    conditions = sum(len(r["conditions"]) for r in docrows)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Authorization_Summary"
    ws.append([name for name, _ in PRIOR] + extended
              + [v.replace("_", " ").title().replace(" ", "_") for v in VOCABULARIES]
              + ["Documents", "Language", "Page_Start", "Page_End"])
    for row in rows:
        first_doc, last_doc = row["documents"][0], row["documents"][-1]
        row_labels = labelled.get(first_doc["file_number"], {})
        line = [None if src == "-" else
                (derive(row, src, queue_by_fn, row_labels) if src.startswith("@")
                 else cell(row["fields"].get(src) or []))
                for _, src in PRIOR]
        line += [cell(row["fields"].get(n) or []) for n in extended]
        line += [label_cell(row_labels.get(v)) for v in VOCABULARIES]
        # The documents are ordered original-then-amendment, which is not page
        # order; a merged row's range is the span of all of them.
        line += ["; ".join(d["doc_id"] for d in row["documents"]),
                 first_doc["language"],
                 min(d["first"] for d in row["documents"]),
                 max(d["last"] for d in row["documents"])]
        ws.append(line)

    cs = wb.create_sheet("Conditions")
    cs.append(["File_Number", "Document", "Section", "Section_Title", "Number",
               "Parent", "Topic", "Deadline", "Text", "Page", "Source"])
    # Once per document, not once per row. A letter granting three
    # authorizations states one set of conditions governing all of them, so
    # writing them per row would print each condition three times and treble a
    # count the document does not treble.
    for row in docrows:
        for c in row["conditions"]:
            num = str(c.get("number") or "")
            cs.append([row["documents"][0]["file_number"], c.get("document"),
                       c.get("section"), c.get("section_title"), num,
                       num.rsplit(".", 1)[0] if "." in num else None,
                       c.get("topic"), c.get("deadline"), c.get("text"), c.get("page"),
                       c.get("source", "text")])

    ds = wb.create_sheet("Discrepancies")
    ds.append(["File_Number", "Field", "Earlier_Value", "Earlier_Pages",
               "Later_Value", "Later_Pages"])
    for d in discrepancies:
        ds.append([d["file_number"], d["field"], d["earlier"], str(d["earlier_pages"]),
                   d["later"], str(d["later_pages"])])

    # Two sheets, because they ask different things of a reader. Everything on
    # Review_Queue is work somebody owes; everything on Provenance is a record of
    # a choice already made, kept so that taking one reader over another is never
    # silent. Filed together, the second buries the first.
    qs = wb.create_sheet("Review_Queue")
    qs.append(["File_Number", "Document", "Field", "Why", "Reason"])
    for q in sorted((q for q in queue if q["kind"] == DECISION),
                    key=lambda q: q["file_number"]):
        qs.append([q["file_number"], q["document"], q["field"], q["why"], q["reason"]])

    ps = wb.create_sheet("Provenance")
    ps.append(["File_Number", "Document", "Field", "Why", "Settled_By"])
    for q in sorted((q for q in queue if q.get("kind") != DECISION),
                    key=lambda q: q["file_number"]):
        ps.append([q["file_number"], q["document"], q["field"], q["why"],
                   "rule" if q["resolved"] else "note"])

    # The release also carries offsetting plans and assessments that no
    # authorization page range covers. They are a finding aid, not extraction:
    # the title is quoted from the page named beside it, and nothing on this
    # sheet is read by a reader or fed to any other sheet.
    sd = wb.create_sheet("Supporting_Documents")
    sd.append(["Title", "Title_Page", "Page_Start", "Page_End", "Notes"])
    for d in json.load(open(os.path.join(HERE, "supporting_documents.json"))):
        sd.append([d["title"], d["title_page"], d["first"], d["last"], d["notes"]])

    ov = wb.create_sheet("Overview")
    ov.append(["Metric", "Value"])
    for k, v in [("Rows in Authorization_Summary", len(rows)),
                 ("Documents read", len(docs)),
                 ("Numbered conditions", conditions),
                 ("Decisions a person owes", sum(1 for q in queue if q.get("kind") == DECISION)),
                 ("Notes worth knowing", sum(1 for q in queue
                                             if q.get("kind") == NOTE and not q["resolved"])),
                 ("Conflicts the rules settled", sum(1 for q in queue if q["resolved"])),
                 ("Discrepancies recorded", len(discrepancies)),
                 ("French documents", sum(1 for d in docs if d["language"] == "french"))]:
        ov.append([k, v])

    ms = wb.create_sheet("Methodology")
    for line in [
        ["How this workbook was made"],
        ["Two readers read each document independently and never saw each other's"],
        ["answers. A value survives only where its quote was found on the page it"],
        ["cites; where the readers disagreed, the cell is empty and the conflict is"],
        ["on the Review_Queue. Every page number is a page of the release."],
        [""],
        ["A cell ending (i) was reasoned from the document rather than quoted from"],
        ["it, and is the one kind of cell that cannot be checked word for word."],
        [""],
        ["Nothing is copied from any earlier summary. An empty cell means this run"],
        ["could not support it from the documents, not that the answer is unknown"],
        ["to anyone."],
    ]:
        ms.append(line)

    for sheet in wb.worksheets:
        for c in sheet[1]:
            c.font = Font(bold=True)
        sheet.freeze_panes = "A2"
        for col in sheet.columns:
            width = max((len(str(c.value)) for c in col[:60] if c.value is not None), default=8)
            sheet.column_dimensions[col[0].column_letter].width = min(max(width + 2, 10), 52)
    wb.save(out_path)
    # Returned rather than recomputed by the caller: the sheet and the number
    # reported for it have to come from the same count.
    return conditions


DECISION, NOTE = "decision", "note"


def dedupe(queue):
    """One row per problem. Both readers hitting the same condition is one
    problem with that condition, not two things to look at."""
    seen, out = set(), []
    for q in queue:
        key = (q["document"], q["field"], q["why"][:60])
        if key in seen:
            continue
        seen.add(key)
        out.append(q)
    return out


# Reasons that are worth knowing but ask nothing of anybody. A queue that files
# advisories as work gets ignored, and then the work in it gets ignored too.
ADVISORY = ("condition_page_break", "both_null")


def classify_queue(entry):
    """Does this need somebody to decide, or is it worth knowing?"""
    return NOTE if entry["reason"] in ADVISORY else DECISION


def write_conflicts(sandbox, queue):
    """What pass C still owes: one entry per conflict nothing has settled."""
    open_ = [q for q in queue if not q["resolved"] and q["kind"] == DECISION]
    json.dump(open_, open(f"{sandbox}/conflicts.json", "w"), indent=1, ensure_ascii=False)
    return open_


def open_conflicts(sandbox):
    """Combine the readers and file what they disagreed about.

    The front half of build(). Separated because it needs no spreadsheet and
    none of its dependencies, so a night that has just read can hand its
    conflicts to an adjudicator instead of waiting for the corpus to finish and
    a workbook to be assembled. Returns the assembled parts build() goes on to
    write, followed by the conflicts nothing has settled.
    """
    rows, docs, queue, discrepancies = assemble(sandbox)
    queue = dedupe(queue)
    for q in queue:
        q["kind"] = NOTE if q["resolved"] else classify_queue(q)
    return rows, docs, queue, discrepancies, write_conflicts(sandbox, queue)


def build(sandbox, out_path):
    rows, docs, queue, discrepancies, _ = open_conflicts(sandbox)
    spec = list(json.load(open(f"{sandbox}/fields.json")))
    conditions = write_workbook(rows, docs, queue, discrepancies, spec, out_path,
                                labels(sandbox))
    return {"rows": len(rows), "documents": len(docs),
            "decisions": sum(1 for q in queue if q.get("kind") == DECISION),
            "notes": sum(1 for q in queue if q.get("kind") == NOTE and not q["resolved"]),
            "auto_resolved": sum(1 for q in queue if q["resolved"]),
            "discrepancies": len(discrepancies),
            "conditions": conditions}


if __name__ == "__main__":
    print(build(sys.argv[1], sys.argv[2]))
