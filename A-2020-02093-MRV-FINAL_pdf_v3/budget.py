"""What the rest of the extraction costs, measured from runs already done.

The subscription meter does not publish a token budget, and the community
reverse-engineering of it is expressed in total tokens including cache reads.
So this counts the same way: input + output + cache-creation + cache-read, summed
across the orchestrating session and every reader it spawned.

Cost per read is measured, not assumed. Feed it the transcripts of a run and the
count of reads that run produced, and it reports what one read costs and what the
remaining work will cost at that rate.

    budget.py <sandbox> [transcript-dir ...]

Weekly ceilings are estimates from outside Anthropic, who publish none. They are
stated here as a parameter rather than a fact, so a better number can replace one
line.
"""
import json, os, re, sys

from paths import resolve
from collections import defaultdict

# Reverse-engineered weekly ceilings, total tokens including cache reads.
# Source: community measurement of ccusage logs against the usage meter.
WEEKLY = {"pro": 125_000_000, "max5x": 1_250_000_000, "max20x": 5_000_000_000}

USAGE_RX = re.compile(
    r'"usage":\{"input_tokens":(\d+),"cache_creation_input_tokens":(\d+),'
    r'"cache_read_input_tokens":(\d+),"output_tokens":(\d+)')
MODEL_RX = re.compile(r'"model":"(claude-[a-z0-9.-]+)"')


def scan(path):
    """Total tokens in one transcript, and the model that dominates it."""
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return 0, None
    total = sum(sum(int(g) for g in m.groups()) for m in USAGE_RX.finditer(text))
    models = MODEL_RX.findall(text)
    top = max(set(models), key=models.count) if models else None
    return total, top


def measure(dirs):
    by_model, files = defaultdict(int), 0
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for name in os.listdir(d):
            if not (name.endswith(".jsonl") or name.endswith(".output")):
                continue
            total, model = scan(os.path.join(d, name))
            if total:
                by_model[model or "unknown"] += total
                files += 1
    return by_model, files


def reads_done(sandbox):
    wave = json.load(open(f"{sandbox}/wave.json"))
    done = sum(1 for o in wave if os.path.exists(resolve(o["out"])))
    return done, len(wave) - done, len(wave)


if __name__ == "__main__":
    sandbox = sys.argv[1]
    dirs = sys.argv[2:] or ["."]
    by_model, files = measure(dirs)
    measured = sum(by_model.values())
    done, remaining, total = reads_done(sandbox)

    print(f"MEASURED, from {files} transcripts")
    for m, t in sorted(by_model.items(), key=lambda kv: -kv[1]):
        print(f"    {m or 'unknown':32s} {t/1e6:9.1f}M  ({t/measured:5.1%})")
    print(f"    {'TOTAL':32s} {measured/1e6:9.1f}M")

    # Reads produced by the transcripts being measured. Passed in because a
    # sandbox carries reads from earlier runs the transcripts know nothing about.
    produced = int(os.environ.get("READS_MEASURED", "0"))
    if not produced:
        print("\nset READS_MEASURED to the reads these transcripts produced")
        sys.exit(0)

    # Reading and orchestrating are different costs and must not be blended.
    # A reader is a short-lived agent on a small context. An orchestrator is one
    # long context re-read on every turn, so its cost scales with how many turns
    # it takes rather than with how much work it dispatches — which is why the
    # cheapest orchestrator is the one that takes the fewest turns.
    READER_MODELS = ("claude-sonnet-5", "claude-haiku-4-5-20251001")
    reading = sum(t for m, t in by_model.items() if m in READER_MODELS)
    orchestration = measured - reading
    per_read = reading / produced

    print(f"\nSPLIT")
    print(f"    reading        {reading/1e6:9.1f}M  -> {per_read/1e3:6.0f}K per read")
    print(f"    orchestration  {orchestration/1e6:9.1f}M  -> {orchestration/reading:5.1f}x the "
          f"work it dispatched")

    print(f"\nREMAINING WORK, reading only  ({remaining} of {total} reads)")
    for label, n, mult in [("reading (pass A+B)", remaining, 1.0),
                           ("adjudication (pass C)", 270, 2.0),
                           ("labelling (pass D)", 9, 3.0)]:
        print(f"    {label:24s} {n:5d} units  {n*per_read*mult/1e6:7.1f}M")
    projected = (remaining + 270 * 2 + 9 * 3) * per_read
    print(f"    {'TOTAL':24s}              {projected/1e6:7.1f}M")

    print("\nORCHESTRATION IS THE VARIABLE THAT MATTERS")
    cap = WEEKLY["max5x"]
    for docs in (2, 4, 8, 16):
        nights = -(-remaining // (docs * 4))
        for turns, per_turn in (("lean", 0.4e6), ("today's", 5.5e6)):
            # a night costs its reads plus its orchestrator's context, re-read per turn
            night = docs * 4 * per_read + (docs * 4) * per_turn
            print(f"    {docs:2d} docs/night, {turns:8s} orchestrator: "
                  f"{night/1e6:7.1f}M/night x {nights:3d} nights = "
                  f"{night*nights/1e9:5.2f}B  ({night/cap*7:6.1%} of weekly per night)")

    print("\nAGAINST A WEEKLY CEILING (reading + lean orchestration only)")
    lean = projected + (remaining + 549) * 0.4e6
    for plan, capv in WEEKLY.items():
        print(f"    {plan:8s} {capv/1e9:5.2f}B/week -> {lean/capv*100:5.1f}% of one week")
