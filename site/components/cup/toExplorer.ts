/**
 * Cup player rows in the shape the fixture pages' pitch already reads.
 *
 * Written so the cups can USE `components/fixture/Pitch` rather than grow a
 * second pitch beside it. The first attempt did grow one, and it was a worse
 * copy: no position badges, no out-of-position ring, no bench values, no key.
 *
 * `expected` is deliberately absent. It is what the model predicts for THIS
 * match, and a cup tie involving a Championship club has no model behind it.
 * The pitch is handed `bases={["career"]}` so it never asks for one, and a
 * copy of `career` wearing the word "expected" would be a lie a reader could
 * not see.
 */

import type { ExplorerRow, Spot, TeamShape } from "@/lib/data";
import type { CupEleven, CupPlayer } from "@/lib/cups";

/** One squad member as an explorer row. Career rates only. */
export function toRow(p: CupPlayer, team: string, opponent: string, fixture: string): ExplorerRow {
  const committed = p.foulsPer90;
  const drawn = p.foulsWonPer90;
  return {
    player: p.player,
    fullName: p.player,
    position: p.position,
    team,
    opponent,
    fixture,
    kickoff: "",
    minutes: p.minutes,
    startProbability: null,
    confirmed: false,
    thin: p.thin,
    career: {
      committed,
      drawn,
      involvements:
        committed != null && drawn != null
          ? Number((committed + drawn).toFixed(2))
          : null,
      nineties: Number((p.minutes / 90).toFixed(1)),
    },
    // The per-line probability ladders. Empty, because they are model output
    // and there is no model here. The pitch never reads them; the explorer,
    // which does, is never handed a cup row.
    committed: [],
    drawn: [],
    involvements: [],
    pmf: { committed: [], drawn: [], involvements: [] },
  };
}

export function toSquad(
  eleven: CupEleven,
  opponent: string,
  fixture: string
): ExplorerRow[] {
  return eleven.squad.map((p) => toRow(p, eleven.team, opponent, fixture));
}

/** The eleven as a pitch shape. */
export function toShape(eleven: CupEleven): TeamShape {
  return {
    formation: eleven.formation,
    // True whenever this is our arrangement rather than the club's. The pitch
    // prints "predicted elevens" off this.
    predicted: !eleven.confirmed,
    lines: eleven.lines.map((line) => line.map(toSpot)),
    bench: [],
  };
}

function toSpot(p: CupPlayer): Spot {
  return {
    player: p.player,
    position: p.position,
    // The source's positionInfo is not carried through, and the pitch only
    // uses `detail` to nudge a slot left or right. Absent is honest.
    detail: "",
    shirt: p.shirt,
  };
}
