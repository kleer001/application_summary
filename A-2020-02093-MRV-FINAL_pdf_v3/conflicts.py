"""What pass C still owes, computed without building the workbook.

A disagreement between two readers is found by combining them, which needs
nothing but the reader output and the standard library. Assembling the workbook
needs openpyxl and the whole corpus; adjudicating a conflict needs neither. This
runs the first without the second, so conflicts can be settled as the documents
that raise them are read.

Run from the repository root:

    python3 A-2020-02093-MRV-FINAL_pdf_v3/conflicts.py run2

Writes <sandbox>/conflicts.json, one entry per conflict nothing has settled, and
prints the count. Exit status is 0 while conflicts are outstanding and 3 when
there are none, so a scheduled run can skip adjudication without a person
deciding it has nothing to do.
"""
import sys

from build import open_conflicts

NONE_OUTSTANDING = 3

if __name__ == "__main__":
    sandbox = sys.argv[1]
    _, docs, queue, _, outstanding = open_conflicts(sandbox)
    settled = sum(1 for q in queue if q["resolved"])
    print(f"{len(outstanding)} conflicts outstanding over {len(docs)} complete "
          f"documents; {settled} already settled -> {sandbox}/conflicts.json")
    sys.exit(NONE_OUTSTANDING if not outstanding else 0)
