/**
 * The rules of the pitch, separated from the drawing of it.
 *
 * This component has produced the same class of bug four times: a player
 * cloned across two slots, an accent breaking a lookup, a dropdown offering a
 * short name into a slot holding a long one, and a shirt number left behind by
 * the player who used to wear it. Every one of them lives in logic that has
 * nothing to do with React, so it is here, where it can be tested.
 *
 * **Everything keys off `who()`, never a display string.** The lineup feed says
 * "Luka Vuskovic", the explorer's full name is "Luka Vušković" and its short
 * name is "Vuskovic". Those are one player and three strings.
 */

import { who } from "./who";
import type { ExplorerRow, Spot, TeamShape } from "./data";

export type Selected = Record<string, string>;

/** A slot on the pitch and whoever is standing in it. */
export type Occupant = {
  key: string;
  spot: Spot;
  row: ExplorerRow | undefined;
  name: string;
  /** Nobody resolved to this slot. It has to look empty, not occupied. */
  vacant: boolean;
};

/**
 * Shirt numbers for everyone in the matchday squad, keyed canonically.
 *
 * The number belongs to the player, not to the slot. Reading it off the slot
 * meant swapping someone in left the previous occupant's number on his chest,
 * which is how a defender ended up wearing a midfielder's shirt and letter.
 *
 * Players outside the named squad have no number anywhere in the feed, so they
 * get none and fall back to a position letter.
 */
export function shirtIndex(shape: TeamShape): Map<string, number> {
  const out = new Map<string, number>();
  for (const spot of [...shape.lines.flat(), ...shape.bench]) {
    if (spot.shirt != null && spot.player) out.set(who(spot.player), spot.shirt);
  }
  return out;
}

/**
 * What to draw inside the marker: his number if we know it, else his position.
 *
 * Never the slot's number. That is the whole point of the function.
 */
export function markerFor(
  shirts: Map<string, number>,
  row: ExplorerRow | undefined,
  spot: Spot
): string {
  if (row) {
    const shirt = shirts.get(who(row.fullName));
    if (shirt != null) return String(shirt);
    return positionCode(row.position);
  }
  return spot.shirt != null ? String(spot.shirt) : positionCode(spot.position);
}

/** FPL codes a squad GKP/DEF/MID/FWD; the league codes a slot G/D/M/F. */
export function positionCode(position: string): string {
  const first = (position || "").charAt(0).toUpperCase();
  // `"GDMF".includes("")` is true, so an empty position returned an empty
  // marker rather than the fallback. Length has to be checked explicitly.
  return first.length === 1 && "GDMF".includes(first) ? first : "M";
}

export function samePosition(a: string, b: string): boolean {
  return positionCode(a) === positionCode(b);
}

/**
 * Is this player standing somewhere his position does not describe?
 *
 * Worth marking, and NOT worth rearranging the team over. The formation used to
 * reflow into position columns the moment anything was swapped, which moved all
 * eleven players to report a fact about one of them.
 */
export function outOfPosition(row: ExplorerRow | undefined, spot: Spot): boolean {
  if (!row) return false;
  return !samePosition(row.position, spot.position);
}

/**
 * Put a player into a slot, and return the next selection.
 *
 * If he is already on the pitch the two EXCHANGE places, because a player can
 * only be in one place at a time. Cloning him was the original bug here.
 */
export function placeInto(
  current: Selected,
  here: Occupant[],
  targetKey: string,
  incoming: string
): Selected {
  const next = { ...current };
  const displaced = here.find((o) => o.key === targetKey);
  const elsewhere = here.find((o) => o.row && who(o.row.fullName) === incoming);

  if (elsewhere?.key === targetKey) return next; // already there, nothing moves

  next[targetKey] = incoming;
  if (elsewhere) {
    if (displaced?.row) next[elsewhere.key] = who(displaced.row.fullName);
    else delete next[elsewhere.key];
  }
  return next;
}

/**
 * The lines of the formation, always as the league published them.
 *
 * A swap changes who stands in a slot. It does not change the shape. Regrouping
 * everyone into position columns on the first substitution was well meant and
 * deeply confusing: one change made all eleven markers move and every letter
 * change at once.
 */
export function lines(shape: TeamShape, here: Occupant[], mirrored: boolean): Occupant[][] {
  const out: Occupant[][] = [];
  let i = 0;
  for (const line of shape.lines) {
    out.push(here.slice(i, i + line.length));
    i += line.length;
  }
  // Anyone beyond the published shape still has to be drawn somewhere.
  if (i < here.length) out.push(here.slice(i));
  return mirrored ? [...out].reverse() : out;
}

/** Who is standing in each slot right now. */
export function occupancy(
  shape: TeamShape,
  squad: ExplorerRow[],
  selected: Selected,
  find: (rows: ExplorerRow[], name: string) => ExplorerRow | undefined
): Occupant[] {
  return shape.lines.flat().map((spot, index) => {
    const key = `${index}`;
    const chosen = selected[key];
    const row = chosen
      ? squad.find((r) => who(r.fullName) === chosen)
      : find(squad, spot.player);

    // When nobody resolves, the slot is EMPTY. It used to fall back to the name
    // the team sheet printed, which drew the previous occupant as though he
    // were standing there: "Rio Ngumoha" appeared on the pitch with a dash for
    // a rate while Ngumoha also sat in the bench list, because the bench is
    // derived from who is actually on the pitch and he was not. One player, two
    // places, and the pitch was the copy that was lying.
    return {
      key,
      spot,
      row,
      name: row?.player ?? "",
      vacant: !row,
    };
  });
}

/** Everyone in the squad who is not currently standing on the pitch. */
export function benchFrom(squad: ExplorerRow[], here: Occupant[]): ExplorerRow[] {
  const onPitch = new Set(here.filter((o) => o.row).map((o) => who(o.row!.fullName)));
  return squad.filter((r) => !onPitch.has(who(r.fullName)));
}
