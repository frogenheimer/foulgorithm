/**
 * Marking a played fixture's ladder against what happened.
 *
 * Betting arithmetic, not optimism: one lost leg kills a slip even while
 * other legs are open, a slip only came in when every leg landed, and a leg
 * the grading never reached stays open rather than counting either way.
 */

import type { Slip, SlipLeg } from "./data";

export type LegOutcome = { won: boolean; observed?: number | null };
export type Outcomes = Record<string, LegOutcome>;

export const legKey = (leg: SlipLeg): string =>
  `${leg.fullName ?? leg.player}|${leg.market}|${leg.line}`;

/** true = landed, false = lost, null = not graded (yet, or ever). */
export function legMark(leg: SlipLeg, outcomes: Outcomes | undefined): boolean | null {
  const held = outcomes?.[legKey(leg)];
  return held == null ? null : held.won;
}

export type Verdict = "came in" | "no" | "open";

export function slipVerdict(slip: Slip, outcomes: Outcomes | undefined): Verdict {
  const marks = slip.legs.map((l) => legMark(l, outcomes));
  if (marks.some((m) => m === false)) return "no";
  if (marks.length && marks.every((m) => m === true)) return "came in";
  return "open";
}

export type BetVerdict = Verdict | "void";

/**
 * A committed bet's verdict, void backstop included: once the game is over,
 * a leg with no graded outcome voids and the bet settles on its remaining
 * legs (docs/38). Before the game is over an ungraded leg keeps the bet
 * open, exactly like slipVerdict.
 */
export function betVerdict(
  legs: SlipLeg[],
  outcomes: Outcomes | undefined,
  gameOver: boolean
): BetVerdict {
  const marks = legs.map((l) => legMark(l, outcomes));
  if (marks.some((m) => m === false)) return "no";
  if (!gameOver) {
    return marks.length && marks.every((m) => m === true) ? "came in" : "open";
  }
  const settled = marks.filter((m) => m !== null);
  if (!settled.length) return "void";
  return "came in";
}
