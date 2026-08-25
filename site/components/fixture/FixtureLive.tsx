"use client";

/**
 * The pitch, with the reader's swaps as its one piece of state.
 *
 * This used to plumb swaps down to an odds-tier ladder at the foot of the
 * page. The ladder is retired (too many "picks" on a site whose picks are
 * the eleven's committed bets), so the swap now only changes who is shown
 * on the pitch, and the sections between arrive server-rendered as children
 * and pass straight through.
 */

import { useState } from "react";
import type { Explorer, Formations } from "@/lib/data";
import { SectionHead } from "@/components/kit";
import Lineups from "./Lineups";

export default function FixtureLive({
  fixture,
  shapes,
  explorer,
  children,
}: {
  fixture: string;
  /** Absent when the league has published no formation lines for this game. */
  shapes?: Formations[string];
  explorer: Explorer;
  children: React.ReactNode;
}) {
  const [selected, setSelected] = useState<Record<string, string>>({});

  return (
    <>
      {shapes && (
        <section>
          <SectionHead
            title="The eleven on the pitch"
            note="Drawn from the league's own formation lines, so a back three and a back four actually look different. Swap anyone to see who else could hold the shirt."
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
