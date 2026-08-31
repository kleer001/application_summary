"""Pass D work order: sort extracted values onto the controlled vocabularies.

Labelling is not reading. A labeller never sees the release — it is handed the
values pass A and pass B already recovered and verified, and decides which term
of a closed list each row belongs under. That is why this runs after the reading
rather than inside it, and why every label the workbook writes carries `(i)`.

One agent per vocabulary, each given every row at once. Sharding by row is what
produced the summary this replaces: 98 projects under 80 distinct labels,
because a labeller that cannot see the other rows invents a term they already
use.

Run from the repository root:

    python3 A-2020-02093-MRV-FINAL_pdf_v3/passd.py <sandbox> [out.xlsx]

Writes `<sandbox>/pass_d_input.json` and prints one work order per vocabulary,
tab-separated: vocabulary, contract, input, output.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VOCAB_MD = os.path.join(HERE, "..", "VOCABULARIES.md")

# The heading each vocabulary is written under, where it differs from the name
# the workbook column uses.
HEADING = {"proponent_type": "Proponent"}

# Only the vocabularies a column is derived from. `VOCABULARIES.md` describes
# more, and labelling against them is work with nowhere to land: the workbook
# reproduces the prior summary's layout, which has a column for aquatic setting
# and one for project type and none for the rest.
VOCABULARIES = ["activity", "sector", "setting"]

# What a labeller is shown of each row. Enough to decide a term and no more: the
# labeller is not being asked to re-read the document, and a longer row is a
# longer context for nine agents at once.
SHOWN = {
    "file_number": "DFO_File_or_PATH",
    "project_description": "Project_Name_or_Description",
    "proponent": "Proponent",
    "province": "Province",
    "waterbody": "waterbody",
    "coordinates": "coordinates",
    "habitat_impact_activities": "habitat_impact_activities",
    "offsetting_measures": "Offsetting_Measures",
    "species_at_risk_finding": "species_at_risk_finding",
    "letter_of_credit_required": "letter_of_credit_required",
}


def terms_for(name):
    """The terms of one vocabulary, from the file the discipline lead edits.

    Two shapes are in that file and both are load-bearing: a markdown table
    where a count was worth recording, and a `·`-separated run where it was
    not. Parsing both means the vocabulary can be edited in either without
    anybody remembering which one this reads.
    """
    heading = HEADING.get(name, name.replace("_", " ")).lower()
    md = open(os.path.abspath(VOCAB_MD), encoding="utf-8").read()
    body = None
    for m in re.finditer(r"^### ([^\n]+)\n(.*?)(?=^### |\Z)", md, re.S | re.M):
        title = m.group(1).split("—")[0].split("(")[0].strip().lower()
        if title == heading:
            body = m.group(2)
            break
    if body is None:
        raise SystemExit(f"no '### {heading}' section in VOCABULARIES.md")

    terms = [re.sub(r"\s*\(\d+\)\s*$", "", c.strip())
             for row in re.findall(r"^\|\s*([^|]+?)\s*\|[^|]*\|\s*$", body, re.M)
             for c in [row] if c.strip() and not set(c.strip()) <= set("- ")]
    if terms:
        return terms
    # The term run is one paragraph. Prose often follows it explaining the
    # list, and taking every remaining line swallows that prose as a term.
    for para in re.split(r"\n\s*\n", body):
        if "·" in para:
            return [re.sub(r"\s*\(\d+\)\s*$", "", t.strip())
                    for t in " ".join(para.split()).split("·") if t.strip()]
    raise SystemExit(f"no terms found under '{heading}'")


def rows_from(xlsx):
    """One dict per row, from both sheets that hold a row's values.

    Five of the values a labeller is shown -- waterbody, coordinates, the habitat
    impact activities, the species-at-risk finding and whether a letter of credit
    is required -- live on Extended_Fields, because the prior layout has no column
    for them. Joined on the identifier the two sheets share. Reading only the
    summary would not fail: `column in header` would simply be false and a
    labeller would be handed None for five fields out of ten and label against
    what was left.
    """
    import openpyxl
    wb = openpyxl.load_workbook(xlsx, data_only=True)
    ws = wb["Authorization_Summary"]
    header = [c.value for c in ws[1]]

    extended = {}
    if "Extended_Fields" in wb.sheetnames:
        es = wb["Extended_Fields"]
        ehdr = [c.value for c in es[1]]
        for r in es.iter_rows(min_row=2, values_only=True):
            d = dict(zip(ehdr, r))
            if d.get("DFO_File_or_PATH"):
                extended[d["DFO_File_or_PATH"]] = d

    out = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        base = dict(zip(header, r))
        # The summary wins where both carry a name: DFO_File_or_PATH and
        # Documents are on both sheets and are the join, not two answers.
        merged = {**extended.get(base.get("DFO_File_or_PATH"), {}), **base}
        row = {}
        for field, column in SHOWN.items():
            v = merged.get(column)
            if v not in (None, ""):
                row[field] = str(v)
        if row.get("file_number"):
            out.append(row)
    return out


def main():
    sandbox = sys.argv[1]
    xlsx = sys.argv[2] if len(sys.argv) > 2 else None
    if not xlsx:
        raise SystemExit("give the built workbook: passd.py <sandbox> <out.xlsx>")

    rows = rows_from(xlsx)
    inp = os.path.abspath(f"{sandbox}/pass_d_input.json")
    json.dump(rows, open(inp, "w"), indent=1)
    os.makedirs(f"{sandbox}/labelled", exist_ok=True)

    vocab_path = os.path.abspath(f"{sandbox}/pass_d_vocabularies.json")
    vocabs = {v: terms_for(v) for v in VOCABULARIES}
    json.dump(vocabs, open(vocab_path, "w"), indent=1)

    print(f"{len(rows)} rows -> {inp}", file=sys.stderr)
    for v in VOCABULARIES:
        print(f"{v}\t{len(vocabs[v])} terms\t{os.path.abspath(HERE)}/contract_d.md"
              f"\t{inp}\t{vocab_path}"
              f"\t{os.path.abspath(sandbox)}/labelled/{v}.json")


if __name__ == "__main__":
    main()
