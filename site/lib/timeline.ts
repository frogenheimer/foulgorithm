/**
 * Which face a homepage card shows.
 *
 * A played game shows what happened; an upcoming game may show the crossover;
 * a game under way shows neither, because the picks bind at kickoff and a
 * card advertising them mid-match is advertising something no longer on
 * offer. Kept out of the component so the rule survives redesigns.
 */

export type CardState = "past" | "live" | "upcoming";
export type CardKind = "played" | "crossover" | "quiet";

export function cardKind(
  state: CardState,
  hasResult: boolean,
  hasOptions: boolean
): CardKind {
  if (hasResult) return "played";
  if (hasOptions && state === "upcoming") return "crossover";
  return "quiet";
}
