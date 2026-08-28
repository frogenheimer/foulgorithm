"use client";

/**
 * The house sheet and the pitch, sharing the one piece of state that binds
 * them: which players a reader has swapped on.
 *
 * The sheet at the top shows the PUBLISHED shouts verbatim until the first
 * swap; from then on it recomputes live (lib/housesheet.ts, a port of the
 * pipeline's selection that has to stay one) from whoever is standing on the
 * pitches, resolved through the same occupancy logic the pitch draws with.
 * The sections in between arrive server-rendered as children and pass
 * straight through.
 */

import { useMemo, useState } from "react";
import type { Bet, Explorer, Formations, HouseSheet as Sheet, SlateShape } from "@/lib/data";
import type { Outcomes } from "@/lib/graded";
import { houseSlipsFrom } from "@/lib/houseslips";
import HouseSlips from "./HouseSlips";
import { SectionHead } from "@/components/kit";
import { houseSheetFrom } from "@/lib/housesheet";
import { onPitchWho } from "@/lib/pitch";
import { findPlayer } from "@/lib/who";
import HouseSheet from "./HouseSheet";
import Lineups from "./Lineups";

export default function FixtureLive({
  fixture,
  shapes,
  explorer,
  houseSheet,
  houseSlips,
  shapes_for_slips,
  outcomes,
  gameOver = false,
  children,
}: {
  fixture: string;
  /** Absent when the league has published no formation lines for this game. */
  shapes?: Formations[string];
  explorer: Explorer;
  /** The pipeline's published sheet, shown until a reader changes a slot. */
  houseSheet?: Sheet | null;
  /** The house's three slips (docs/45), recomputed from swaps like the sheet. */
  houseSlips?: Record<string, Bet> | null;
  shapes_for_slips?: SlateShape[];
  outcomes?: Outcomes;
  gameOver?: boolean;
  children: React.ReactNode;
}) {
  const [selected, setSelected] = useState<Record<string, string>>({});
  const changed = Object.keys(selected).length > 0;

  const onPitch = useMemo(() => {
    if (!changed || !shapes) return null;
    const clubs = fixture.split(" v ").filter((c) => shapes[c]);
    const squads = Object.fromEntries(
      clubs.map((club) => [club, explorer.rows.filter((r) => r.fixture === fixture && r.team === club)])
    );
    return onPitchWho(shapes, clubs, selected, squads, findPlayer);
  }, [changed, shapes, explorer, fixture, selected]);

  const slips = useMemo(() => {
    if (!houseSlips) return null;
    if (!onPitch) return houseSlips;
    return houseSlipsFrom(explorer, fixture, onPitch);
  }, [houseSlips, onPitch, explorer, fixture]);

  const sheet = useMemo(() => {
    if (!changed || !shapes) return houseSheet;
    const clubs = fixture.split(" v ").filter((c) => shapes[c]);
    const squads = Object.fromEntries(
      clubs.map((club) => [
        club,
        explorer.rows.filter((r) => r.fixture === fixture && r.team === club),
      ])
    );
    const onPitch = onPitchWho(shapes, clubs, selected, squads, findPlayer);
    return houseSheetFrom(explorer, fixture, onPitch);
  }, [changed, shapes, explorer, fixture, selected, houseSheet]);

  return (
    <>
      {slips && (
        <section>
          <SectionHead
            title={changed ? "The house · your eleven" : "The house"}
            note={
              changed
                ? "Recomputed live from the eleven you chose on the pitch below. Reset the pitch to see the published slips again."
                : "The model's own three slips: safe needs four foul events, optimistic five, rogue six. Priced by its own numbers, graded like the eleven's, never in the league."
            }
          />
          <HouseSlips slips={slips} shapes={shapes_for_slips ?? []} outcomes={outcomes} gameOver={gameOver} />
        </section>
      )}

      {sheet && sheet.groups.length > 0 && <HouseSheet sheet={sheet} rebuilt={changed} />}

      {shapes && (
        <section>
          <SectionHead
            title="The eleven on the pitch"
            note={
              houseSheet
                ? "Drawn from the league's own formation lines, so a back three and a back four actually look different. Swap anyone and the house sheet at the top recomputes from the eleven you chose."
                : "Drawn from the league's own formation lines, so a back three and a back four actually look different. Swap anyone and the house's slips at the top are rebuilt from the eleven you chose."
            }
          />
          <Lineups
            fixture={fixture}
            shapes={shapes}
            explorer={explorer}
            selected={selected}
            onChange={setSelected}
          />
        </section>
      )}

      {children}
    </>
  );
}
