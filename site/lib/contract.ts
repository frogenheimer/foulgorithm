/**
 * The contract, said once (docs/38, docs/45).
 *
 * The table's subtitle, the fixture page's bets note and the methodology page
 * all describe how the eleven bet and how the league scores them. They used
 * to each carry their own sentence, and the methodology page still said
 * "five characters" and "fixed slates each gameweek" a week after both had
 * changed. One module reads the era off the payload's shapes and every
 * surface says the same thing; a guard test keeps it that way.
 */

import type { SlateShape } from "./data";

export function isPriced(shapes: SlateShape[] | undefined): boolean {
  return (shapes ?? []).some((sh) => sh.units != null || sh.target != null);
}

/** How the eleven bet, one sentence, for any surface. */
export function betsCopy(priced: boolean): string {
  return priced
    ? "On every game, every one of the eleven makes three slips: safe needs four foul events to land, optimistic five, rogue six, any layout inside the count, with the house's price printed on each."
    : "On every game, every one of the eleven commits to the same three bets: six players at 1+, three at 2+, and a mixed two-and-two.";
}

/** The scoring rule, one sentence, for any surface. */
export function scoringCopy(priced: boolean): string {
  return priced
    ? "Every leg lands is a win, one foul short in total is a draw, anything worse a loss."
    : "Every leg lands is a win, all but one is a draw, anything worse a loss.";
}

export function contractCopy(shapes: SlateShape[] | undefined) {
  const priced = isPriced(shapes);
  return { priced, bets: betsCopy(priced), scoring: scoringCopy(priced) };
}
