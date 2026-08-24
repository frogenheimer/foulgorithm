"use client";

/**
 * Both elevens on pitches, and the five characters rebuilt from them.
 *
 * The point of the swap is not the pitch. It is that a reader can ask "what if
 * he is rested" and get an answer, instead of being told to wait for team news.
 * Change a slot and every combination on the page is recomputed from the eleven
 * now standing on it.
 *
 * Recomputed, not re-requested: within one fixture the opponent and
 * head-to-head factors are settled, so each player's probability per market and
 * line is already shipped. A swap swaps one contribution.
 */

import { useMemo, useState } from "react";
import type { Explorer, ExplorerRow, Formations, Slip } from "@/lib/data";
import { Callout } from "@/components/kit";
import { findPlayer, who } from "@/lib/who";
import type { Basis } from "./Pitch";
import Pitch from "./Pitch";
import type { Market } from "./Pitch";
import { candidatesFor, slipAtOdds } from "./rebuild";
import s from "./pitch.module.css";

const TIERS: [number, string][] = [
  [3, "2/1"],
  [4, "3/1"],
  [6, "5/1"],
  [11, "10/1"],
  [21, "20/1"],
];

export default function Lineups({
  fixture,
  shapes,
  explorer,
  published,
}: {
  fixture: string;
  shapes: Formations[string];
  explorer: Explorer;
  /** What the pipeline published, used until a reader changes something. */
  published: Record<string, Slip[]>;
}) {
  const [selected, setSelected] = useState<Record<string, string>>({});
  const [market, setMarket] = useState<Market>("committed");
  const [basis, setBasis] = useState<Basis>("match");
  // Narrow screens show one side at a time; both fit side by side above 900px.

  // Home first, away second, matching the fixture label rather than object order.
  const [homeClub, awayClub] = fixture.split(" v ");
  const clubs = [homeClub, awayClub].filter((c) => shapes[c]);

  const squads = useMemo(() => {
    const out: Record<string, ExplorerRow[]> = {};
    for (const club of clubs) {
      out[club] = explorer.rows.filter((r) => r.fixture === fixture && r.team === club);
    }
    return out;
  }, [explorer.rows, fixture, clubs]);

  // Who is on the pitch right now, published eleven with any swaps applied.
  const onPitch = useMemo(() => {
    const names = new Set<string>();
    for (const club of clubs) {
      shapes[club]?.lines.forEach((line, i) =>
        line.forEach((spot, j) => {
          // Slots hold a canonical key once swapped and a lineup-feed name
          // before that. Both resolve to the same row, and the candidate list
          // keys on that row's own short name.
          const chosen = selected[`${club}|${i}|${j}`];
          const row = chosen
            ? (squads[club] ?? []).find((r) => who(r.fullName) === chosen)
            : findPlayer(squads[club] ?? [], spot.player);
          if (row) names.add(row.player);
        })
      );
    }
    return names;
  }, [shapes, selected, clubs, squads]);

  const changed = Object.keys(selected).length > 0;

  const slips = useMemo(() => {
    if (!changed) return published;
    const rows = clubs.flatMap((c) => squads[c]);
    const candidates = candidatesFor(rows, explorer.lines, onPitch);
    const out: Record<string, Slip[]> = {};
    explorer.models.forEach((model, i) => {
      const ladder = TIERS.map(([t, label]) => slipAtOdds(candidates, i, t, label)).filter(
        (x): x is Slip => x !== null
      );
      if (ladder.length) out[model] = ladder;
    });
    return out;
  }, [changed, published, clubs, squads, explorer.lines, explorer.models, onPitch]);

  // Three sources, three spellings. See lib/who.ts.
  const findRow = (club: string, player: string) =>
    findPlayer(squads[club] ?? [], player);

  return (
    <div style={{ display: "grid", gap: "var(--s6)" }}>
      <Pitch
        home={{ club: homeClub, shape: shapes[homeClub], squad: squads[homeClub] ?? [] }}
        away={{ club: awayClub, shape: shapes[awayClub], squad: squads[awayClub] ?? [] }}
        selected={selected}
        onChange={setSelected}
        onReset={() => setSelected({})}
        market={market}
        onMarket={setMarket}
        basis={basis}
        onBasis={setBasis}
      />

      {changed && (
        <Callout>
          <strong>Rebuilt from your eleven.</strong> Every combination below now uses the
          players on those pitches, not the published lineup. Nothing here is graded: the
          record only ever contains what we actually published before kickoff.
        </Callout>
      )}

    </div>
  );
}
