"""The DFO file-number shape, and the corrections to it, in one place.

A file number is the row key. Everything a document contributes to the workbook
is filed under it, so a wrong one does not produce a wrong cell — it produces a
row nothing can find and conditions belonging to nobody.

The segmenter reads the OCR text, which sometimes does not carry the header at
all. Readers are given the scan as well, so where both of them agree on a number
that is not the one the segment was keyed on, they are looking at something the
segmenter could not see. Those cases are recorded in `corrections.json` with the
evidence and applied here, rather than edited into `segs.json` — segmentation is
regenerated, and an edit to its output would be silently lost the next time.
"""
import functools
import json
import os
import re

FILE_RX = re.compile(r"\d{2}-H[A-Z]{3}-\d{5}")
# The whole of a key, not a match found inside prose. A row key that is an
# authorization number ("Auth 2019-039") passes no test that looks for a file
# number somewhere in a string, and fails this one.
KEY_RX = re.compile(r"\A\d{2}-H[A-Z]{3}-\d{5}\Z")

HERE = os.path.dirname(os.path.abspath(__file__))
CORRECTIONS = os.path.join(HERE, "corrections.json")


def is_file_number(value):
    return bool(KEY_RX.match(str(value or "")))


@functools.lru_cache(maxsize=1)
def corrections():
    """stem -> the file number the document itself carries."""
    if not os.path.exists(CORRECTIONS):
        return {}
    return {stem: c["file_number"] for stem, c in json.load(open(CORRECTIONS)).items()}


def corrected(stem, file_number):
    """The key a document should be filed under, correction applied."""
    return corrections().get(stem, file_number)
