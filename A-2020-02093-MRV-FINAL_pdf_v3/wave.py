"""Stage a wave and write the work order for it.

Which model reads a document is a fact about the document, not a judgement the
orchestrator makes. This writes it down: one entry per reader, naming the model,
the paths, and where the answer goes. An orchestrator carrying no instructions at
all can execute this file correctly, which is the point — an instruction living
only in an agent definition is one nobody can see and nobody can version.
"""
import json, os, sys
from collections import Counter

from stage import stage, stage_sandbox

# Pass A is bounded fields; pass B is enumeration, which is a completeness task
# and reads on the stronger model regardless of language.
MODEL_A = {"english": "haiku", "french": "sonnet"}
MODEL_B = {"english": "sonnet", "french": "sonnet"}
PASSES = {"a": ("contract_a.md", MODEL_A), "b": ("contract_b.md", MODEL_B)}
HERE = os.path.dirname(os.path.abspath(__file__))


def build_wave(file_numbers, sandbox, segs_path=None):
    segs = json.load(open(segs_path or os.path.join(HERE, "segs.json")))
    by_fn = {}
    for s in segs:
        by_fn.setdefault(s["file_no"], []).append(s)

    stage_sandbox(sandbox)

    orders = []
    for fn in file_numbers:
        for s in sorted(by_fn.get(fn, []), key=lambda x: x["start"]):
            doc_id = f"{fn}#{s['start']}"
            safe = doc_id.replace("#", "_")
            lang = stage(safe, s["start"], s["end"], sandbox)["language"]
            for pass_name, (contract, models) in PASSES.items():
                for reader in ("1", "2"):
                    orders.append({
                        "doc_id": doc_id, "file_number": fn, "stem": safe,
                        "first_page": s["start"], "last_page": s["end"],
                        "language": lang, "pass": pass_name, "reader": reader,
                        "model": models[lang],
                        "contract": f"{sandbox}/{contract}",
                        "fields": f"{sandbox}/fields.json",
                        "slice": f"{sandbox}/slices/{safe}.txt",
                        "pdf": f"{sandbox}/pages/{safe}.pdf",
                        "out": f"{sandbox}/out/{safe}.{pass_name}{reader}.json",
                    })
    json.dump(orders, open(f"{sandbox}/wave.json", "w"), indent=1)
    return orders


if __name__ == "__main__":
    sandbox = sys.argv[1]
    if sys.argv[2] == "--split":                      # e.g. --split tune
        sel = json.load(open(os.path.join(HERE, "split.json")))[sys.argv[3]]
    elif sys.argv[2] == "--all":
        sel = sorted({s["file_no"] for s in json.load(open(os.path.join(HERE, "segs.json")))})
    else:
        sel = sys.argv[2:]
    if "--limit" in sys.argv:
        sel = sel[:int(sys.argv[sys.argv.index("--limit") + 1])]
    orders = build_wave(sel, sandbox)
    docs = {o["doc_id"] for o in orders}
    print(f"wave: {len(sel)} file numbers, {len(docs)} documents, {len(orders)} reads")
    print(f"  by model: {dict(Counter(o['model'] for o in orders))}")
    print(f"  by pass:  {dict(Counter(o['pass'] for o in orders))}")
    print(f"  work order: {sandbox}/wave.json")
