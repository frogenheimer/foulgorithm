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
