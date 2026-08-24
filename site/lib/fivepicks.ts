/**
 * Row derivation for the five-picks matrix.
 *
 * Rows are players, columns are the five, and a filled cell is a committed
 * pick at its line. A character backs a player once no matter how many of his
 * shapes the player sits in, so "backers" counts characters, not appearances,
 * and agreement is what rises to the top.
 */

import type { FixtureBoard, Slates } from "./data";

export type MatrixRow = {
  /** Unique per row: the full name and market, so two Wards never share one. */
  key: string;
  player: string;
  market: string;
  /** character id -> the line the pick was made at, e.g. "2+". */
  byCharacter: Record<string, string>;
  backers: number;
};

export function matrixRows(
  slates: Slates,
  fixture: string,
  characterIds: string[]
): MatrixRow[] {
  const rows = new Map<string, MatrixRow>();

  for (const id of characterIds) {
    const own = slates.byCharacter[id];
    if (!own) continue;
    for (const shape of slates.shapes) {
      for (const leg of own[shape.key]?.legs ?? []) {
        if (leg.fixture !== fixture) continue;
        const key = `${leg.fullName ?? leg.player}|${leg.market}`;
        const row =
          rows.get(key) ??
          ({ key, player: leg.player, market: leg.market, byCharacter: {}, backers: 0 } as MatrixRow);
        if (!row.byCharacter[id]) {
          row.byCharacter[id] = `${leg.fouls}+`;
          row.backers += 1;
        }
        rows.set(key, row);
      }
    }
  }

  return [...rows.values()].sort(
    (a, b) => b.backers - a.backers || a.player.localeCompare(b.player)
  );
}

/**
 * Every game the round's slates touch, once each, in kickoff order. Slate legs
 * carry no kickoff of their own, so the board supplies the order; a game the
 * board does not know sorts after the known ones, alphabetically.
 */
export function slateFixtures(slates: Slates, board: FixtureBoard[]): string[] {
  const seen = new Set<string>();
  for (const own of Object.values(slates.byCharacter)) {
    if (!own) continue;
    for (const shape of slates.shapes) {
      for (const leg of own[shape.key]?.legs ?? []) seen.add(leg.fixture);
    }
  }

  const kickoff = new Map(board.map((f) => [`${f.home} v ${f.away}`, f.kickoff]));
  return [...seen].sort((a, b) => {
    const ka = kickoff.get(a);
    const kb = kickoff.get(b);
    if (ka && kb && ka !== kb) return ka < kb ? -1 : 1;
    if (ka && !kb) return -1;
    if (!ka && kb) return 1;
    return a.localeCompare(b);
  });
}
