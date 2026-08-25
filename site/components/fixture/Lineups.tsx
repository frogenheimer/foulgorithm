"use client";

/**
 * Both elevens on pitches.
 *
 * The point of the swap is not the pitch. It is that a reader can ask "what if
 * he is rested" and get an answer, instead of being told to wait for team news.
 * Change a slot and the house sheet at the top is recomputed from the eleven
 * now standing on it.
 *
 * The swap state itself lives in FixtureLive, because the sheet that consumes
 * it sits at the other end of the page. This component only draws the pitches
 * and reports changes upward.
 */

import { useMemo, useState } from "react";
import type { Explorer, ExplorerRow, Formations } from "@/lib/data";
import { Callout } from "@/components/kit";
import type { Basis } from "./Pitch";
import Pitch from "./Pitch";
import type { Market } from "./Pitch";

export default function Lineups({
  fixture,
  shapes,
  explorer,
  selected,
  onChange,
}: {
  fixture: string;
  shapes: Formations[string];
  explorer: Explorer;
  /** slot key -> canonical player key, owned by FixtureLive. */
  selected: Record<string, string>;
  onChange: (next: Record<string, string>) => void;
}) {
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

  const changed = Object.keys(selected).length > 0;

  return (
    <div style={{ display: "grid", gap: "var(--s6)" }}>
      <Pitch
        home={{ club: homeClub, shape: shapes[homeClub], squad: squads[homeClub] ?? [] }}
        away={{ club: awayClub, shape: shapes[awayClub], squad: squads[awayClub] ?? [] }}
        selected={selected}
        onChange={onChange}
        onReset={() => onChange({})}
        market={market}
        onMarket={setMarket}
        basis={basis}
        onBasis={setBasis}
      />

      {changed && (
        <Callout>
          <strong>Rebuilt from your eleven.</strong> The house sheet at the top now
          uses the players on those pitches, not the published lineup. Nothing here is
          graded: the record only ever contains what we actually published before
          kickoff.
        </Callout>
      )}

    </div>
  );
}
