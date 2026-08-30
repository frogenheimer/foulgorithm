"use client";

/**
 * The house's slips, its full sheet, and the pitch, sharing the one piece of
 * state that binds them: which players a reader has swapped on.
 *
 * The slips at the top show the PUBLISHED bets verbatim until the first
 * swap; from then on they are recomputed live (lib/houseslips.ts, a port of
 * the pipeline's recipes that has to stay one) from whoever is standing on
 * the pitches, resolved through the same occupancy logic the pitch draws
 * with. The full sheet, every shout by line, sits under the slips in a
 * disclosure (docs/51) and follows the same swaps through lib/housesheet.ts.
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
import s from "./fixturelive.module.css";

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
  /** The pipeline's published sheet: every shout by line, under the slips. */
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
    if (!houseSheet) return null;
    if (!onPitch) return houseSheet;
    return houseSheetFrom(explorer, fixture, onPitch);
  }, [houseSheet, onPitch, explorer, fixture]);

  const hasSheet = Boolean(sheet && sheet.groups.length > 0);

  return (
    <>
      {(slips || hasSheet) && (
        <section>
          <SectionHead
            title={changed ? "The house · your eleven" : "The house"}
            note={
              changed
                ? "Recomputed live from the eleven you chose on the pitch below. Reset the pitch to see the published slips again."
                : slips
                  ? "The model's own three slips: safe needs four foul events, optimistic five, rogue six. Priced by its own numbers, graded like the eleven's, never in the league."
                  : "The model's own shouts for this game, priced by its own numbers and never in the league."
            }
          />
          <div className={s.stack}>
            {slips && (
              <HouseSlips
                slips={slips}
                shapes={shapes_for_slips ?? []}
                outcomes={outcomes}
                gameOver={gameOver}
              />
            )}
            {hasSheet && sheet && (
              <details className={s.sheet} open={!slips}>
                <summary className={s.sheetHead}>
                  Every shout by line
                  <span className={s.sheetHint}>
                    {changed ? "your eleven" : "the full sheet, 1+ to 3+"}
                  </span>
                </summary>
                <div className={s.sheetBody}>
                  <HouseSheet sheet={sheet} rebuilt={changed} />
                </div>
              </details>
            )}
          </div>
        </section>
      )}

      {shapes && (
        <section>
          <SectionHead
            title="The eleven on the pitch"
            note="Drawn from the league's own formation lines, so a back three and a back four actually look different. Swap anyone and the house's slips and sheet at the top are rebuilt from the eleven you chose."
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
