"""What the workbook actually cost, measured from the session transcripts.

Calendar time is not the answer. The reading was paced by a nightly schedule set
to stay inside a usage window, so the span from first read to last is an artefact
of that schedule rather than of the work. This measures the two figures that do
transfer to another run: tokens consumed, and time an agent was actually working.

Active time is summed per agent from the timestamps on its own messages, so
agents running concurrently are counted once each rather than collapsed into one
wall-clock span. Gaps longer than IDLE_GAP are treated as the agent waiting on
something outside itself and excluded.

    measure_run.py <transcript-root>
"""
import json, os, sys, datetime
from collections import defaultdict

IDLE_GAP = 300  # seconds; a longer gap is not the agent working


def parse(path):
    """(tokens_by_model, active_seconds, first_ts, last_ts) for one transcript."""
    by_model, stamps = defaultdict(int), []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            msg = rec.get("message") or {}
            usage = msg.get("usage") or {}
            if usage:
                tokens = (usage.get("input_tokens", 0)
                          + usage.get("cache_creation_input_tokens", 0)
                          + usage.get("cache_read_input_tokens", 0)
                          + usage.get("output_tokens", 0))
                by_model[msg.get("model") or "unknown"] += tokens
            ts = rec.get("timestamp")
            if ts:
                try:
                    stamps.append(datetime.datetime.fromisoformat(
                        ts.replace("Z", "+00:00")).timestamp())
                except ValueError:
                    pass
    stamps.sort()
    active = sum(b - a for a, b in zip(stamps, stamps[1:]) if b - a <= IDLE_GAP)
    return by_model, active, (stamps[0] if stamps else None), (stamps[-1] if stamps else None)


def walk(root):
    for dirpath, _, names in os.walk(root):
        for name in names:
            if name.endswith(".jsonl"):
                yield os.path.join(dirpath, name)


def main(root):
    agents = {"total": defaultdict(int), "active": 0.0, "count": 0}
    driver = {"total": defaultdict(int), "active": 0.0, "count": 0}
    span = [None, None]

    for path in walk(root):
        by_model, active, first, last = parse(path)
        if not by_model:
            continue
        bucket = agents if os.sep + "subagents" + os.sep in path else driver
        for model, n in by_model.items():
            bucket["total"][model] += n
        bucket["active"] += active
        bucket["count"] += 1
        for i, t in enumerate((first, last)):
            if t and (span[i] is None or (t < span[i] if i == 0 else t > span[i])):
                span[i] = t

    def show(label, b):
        total = sum(b["total"].values())
        print(f"\n{label}: {b['count']} transcripts")
        print(f"  tokens        {total:,}")
        for model, n in sorted(b["total"].items(), key=lambda kv: -kv[1]):
            print(f"    {model:<40} {n:>15,}")
        print(f"  active time   {b['active']/3600:.1f} h")
        if b["count"]:
            print(f"  per transcript  {total//b['count']:,} tokens, "
                  f"{b['active']/b['count']/60:.1f} min")
        return total

    a = show("Readers and adjudicators (subagents)", agents)
    d = show("Orchestrating sessions", driver)

    print(f"\nCombined tokens        {a+d:,}")
    print(f"Combined active time   {(agents['active']+driver['active'])/3600:.1f} h")
    if a:
        print(f"Orchestration overhead {d/a:.1f}x the work it dispatched")
    if all(span):
        wall = (span[1] - span[0]) / 86400
        print(f"\nCalendar span          {wall:.1f} days "
              f"({datetime.date.fromtimestamp(span[0])} to "
              f"{datetime.date.fromtimestamp(span[1])}) — schedule, not work")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
