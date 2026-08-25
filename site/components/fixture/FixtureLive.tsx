"use client";

/**
 * Owns the one piece of state two ends of the fixture page share: which
 * players a reader has swapped onto the pitch.
 *
 * The pitch sits near the top of the page and the ladder it rebuilds sits at
 * the bottom, with sections between them that care about neither. The page is
 * a server component, so the shared state lives here: the pitch reports swaps
 * up, the ladder recomputes from them, and the sections in between arrive
 * server-rendered as children and pass straight through.
 */

import { useMemo, useState } from "react";
import type { Explorer, Formations, Slip } from "@/lib/data";
import type { Outcomes } from "@/lib/graded";
import { SectionHead } from "@/components/kit";
import { ladderFor, onPitchFrom, squadsFor } from "@/lib/ladder";
import Lineups from "./Lineups";
import SlipGrid from "./SlipGrid";

export default function FixtureLive({
  fixture,
  shapes,
  explorer,
  published,
  characters,
  outcomes,
  children,
}: {
  fixture: string;
  /** Absent when the league has published no formation lines for this game. */
  shapes?: Formations[string];
  explorer: Explorer;
  /** The pipeline's ladder, shown until a reader changes something. */
  published: Record<string, Slip[]>;
  characters: { id: string; name: string }[];
  /** Present on a played game: the ladder's legs settle against these. */
  outcomes?: Outcomes;
  children: React.ReactNode;
}) {
  const [selected, setSelected] = useState<Record<string, string>>({});
  const changed = Object.keys(selected).length > 0;

  const slips = useMemo(() => {
    if (!changed || !shapes) return published;
    const [homeClub, awayClub] = fixture.split(" v ");
    const clubs = [homeClub, awayClub].filter((c) => shapes[c]);
    const squads = squadsFor(explorer, fixture, clubs);
    const onPitch = onPitchFrom(shapes, clubs, selected, squads);
    return ladderFor(explorer, fixture, onPitch, changed, published);
  }, [changed, shapes, explorer, fixture, selected, published]);

  return (
    <>
      {shapes && (
        <section>
          <SectionHead
            title="The eleven on the pitch"
            note="Drawn from the league's own formation lines, so a back three and a back four actually look different. Swap anyone and the ladder at the foot of the page is rebuilt from the eleven you chose."
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

      <section>
        <SectionHead
          title={
            changed
              ? "The ladder, rebuilt from your eleven"
              : outcomes
                ? "The ladder, marked"
                : "The ladder"
          }
          note="What each character would combine to reach each target price, 2/1 out to 20/1. Working combinations, not the committed picks: nothing here is graded, and the picks that score for the league table live on The five."
        />
        <SlipGrid
          slips={slips}
          characters={characters.map((ch) => ch.id)}
          names={Object.fromEntries(characters.map((ch) => [ch.id, ch.name]))}
          outcomes={outcomes}
        />
      </section>
    </>
  );
}
