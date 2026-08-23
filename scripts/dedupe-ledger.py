#!/usr/bin/env python3
"""Remove repeated rows from the prediction ledger.

The store is append-only and that is deliberate: a claim is never edited and
never deleted. This does not break that. A repeated row is the same claim
written more than once, so dropping the later copies removes no claim and
changes no probability. Every distinct claim survives, with its original
published_at.

The repeats came from two places, both now fixed:

  - append() checked the file but not the batch it was handed, so a run that
    emitted a claim twice wrote it twice.
  - A character's tiered slips emitted one row per tier, and the tier was not
    part of the claim's identity, so a player carried across four tiers became
    four identical rows.

Grading joins on the claim, so each repeat was a double-counted bet.

Run with --apply to write. Without it, reports and changes nothing.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

STORE = Path("data/predictions")


def main(apply: bool) -> int:
    total_removed = 0
    for path in sorted(STORE.glob("*.jsonl")):
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        seen: set[str] = set()
        kept = []
        for row in rows:
            if row["key"] in seen:
                continue
            seen.add(row["key"])
            kept.append(row)

        removed = len(rows) - len(kept)
        if not removed:
            continue
        total_removed += removed

        repeats = Counter(r["key"] for r in rows)
        worst = sorted(repeats.items(), key=lambda kv: -kv[1])[:3]
        by_key = {r["key"]: r for r in rows}
        print(f"{path}  {len(rows)} rows, {removed} repeats")
        for key, n in worst:
            if n > 1:
                r = by_key[key]
                print(f"    {n}x  {r['fixture']:<24}{r['entity']:<16}{r['model_id']:<8}{r['line']}")

        if apply:
            path.write_text("".join(json.dumps(r) + "\n" for r in kept))

    if not total_removed:
        print("no repeats found")
    elif apply:
        print(f"\nremoved {total_removed} repeated rows, every distinct claim kept")
    else:
        print(f"\nwould remove {total_removed} repeated rows. Re-run with --apply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main("--apply" in sys.argv))
