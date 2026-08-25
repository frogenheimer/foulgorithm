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
import type { Explorer, Formations, HouseSheet as Sheet } from "@/lib/data";
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
  children,
}: {
  fixture: string;
  /** Absent when the league has published no formation lines for this game. */
  shapes?: Formations[string];
  explorer: Explorer;
  /** The pipeline's published sheet, shown until a reader changes a slot. */
  houseSheet?: Sheet | null;
  children: React.ReactNode;
}) {
  const [selected, setSelected] = useState<Record<string, string>>({});
  const changed = Object.keys(selected).length > 0;

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
      {sheet && sheet.groups.length > 0 && <HouseSheet sheet={sheet} rebuilt={changed} />}

      {shapes && (
        <section>
          <SectionHead
            title="The eleven on the pitch"
            note="Drawn from the league's own formation lines, so a back three and a back four actually look different. Swap anyone and the house sheet at the top recomputes from the eleven you chose."
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
