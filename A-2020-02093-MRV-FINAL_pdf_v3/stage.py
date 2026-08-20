"""Stage one authorization into the sandbox: page-marked OCR text + its PDF pages.

Also reports the document's language, which decides which model reads it. In the
pre-flight, Haiku readers answered a French document in English beside their own
French quotes, which leaves every such cell unverifiable and discarded.

The release text and PDF are opened once per process, not once per document: the
PDF is 356 MB and a wave stages 129 documents out of it.
"""
import functools, json, os, re, shutil, sys

from pypdf import PdfReader, PdfWriter

HERE = os.path.dirname(os.path.abspath(__file__))
RELEASE = json.load(open(os.path.join(HERE, "release.json")))

FR = re.compile(r"[éèêàçôûïî]|\b(les|des|du|sur|dans|aux|sera|selon|doit)\b", re.I)
EN = re.compile(r"\b(the|shall|of|and|with|from|which)\b", re.I)


def language(text):
    """french where French markers carry the page, english where they do not."""
    fr, en = len(FR.findall(text)), len(EN.findall(text))
    return "french" if fr > 20 and fr > en * 0.25 else "english"


@functools.lru_cache(maxsize=1)
def release_pages():
    return open(RELEASE["ocr_text"], encoding="utf-8", errors="replace").read().split("\f")


@functools.lru_cache(maxsize=1)
def release_pdf():
    return PdfReader(RELEASE["pdf"])


def stage(doc_id, start, end, sandbox):
    """Write one document's excerpt and pages. Returns its map."""
    pages = release_pages()
    out = [f"=== document {doc_id}: {end - start + 1} pages ===\n"
           f"Pages are numbered 1 to {end - start + 1} here and in the PDF beside "
           f"this file. The two are the same pages in the same order."]
    for n in range(start, end + 1):
        out.append(f"=== page {n - start + 1} ===\n{pages[n - 1].rstrip()}")
    body = "\n\n".join(out)
    open(f"{sandbox}/slices/{doc_id}.txt", "w", encoding="utf-8").write(body)

    reader, writer = release_pdf(), PdfWriter()
    for n in range(start, end + 1):
        writer.add_page(reader.pages[n - 1])
    with open(f"{sandbox}/pages/{doc_id}.pdf", "wb") as fh:
        writer.write(fh)

    doc_map = {"doc_id": doc_id, "first": start, "last": end,
               "pages": end - start + 1, "language": language(body)}
    json.dump(doc_map, open(f"{sandbox}/{doc_id}.map.json", "w"))
    return doc_map


def stage_sandbox(sandbox):
    """The inputs every reader in a wave shares, written once."""
    for sub in ("slices", "pages", "out"):
        os.makedirs(f"{sandbox}/{sub}", exist_ok=True)
    for name in ("contract_a.md", "contract_b.md", "fields.json"):
        shutil.copy(os.path.join(HERE, name), f"{sandbox}/{name}")


if __name__ == "__main__":
    doc_id, start, end, sandbox = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    stage_sandbox(sandbox)
    m = stage(doc_id, start, end, sandbox)
    print(f"staged {doc_id}: {m['pages']} pages, {m['language']} -> {sandbox}")
