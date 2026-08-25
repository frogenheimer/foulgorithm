/**
 * What we call the things we predict, in one place.
 *
 * The same market was called "Fouls committed" on the pitch and in the explorer,
 * "Fouls committed" on the fixture board and in the methodology, and "fouls
 * committed" in prose. `MARKET_LABEL` was defined twice, once here and once in
 * the explorer, and the fixture board had a third set inline. A reader moving
 * from the homepage to a player page had no way to know they were the same
 * number.
 *
 * One market, one name, everywhere.
 */

export type Market = "committed" | "drawn" | "involvements";

/** The name on a tab, a toggle or a column head. */
export const MARKET_LABEL: Record<Market, string> = {
  committed: "Fouls committed",
  drawn: "Fouls won",
  involvements: "Involvements",
};

/** The name inside a sentence, where the tab label would read oddly. */
export const MARKET_PROSE: Record<Market, string> = {
  committed: "fouls committed",
  drawn: "fouls won",
  involvements: "foul involvements",
};

/** What one of them is, for a tooltip or a first mention. */
export const MARKET_MEANING: Record<Market, string> = {
  committed: "fouls he gives away",
  drawn: "fouls won by him",
  involvements: "both together, either side of the challenge",
};

export const MARKETS: Market[] = ["committed", "drawn", "involvements"];

/**
 * A forecast, written as a count out of a hundred.
 *
 * The site uses two notations on purpose and the difference carries meaning:
 *
 *   - **`64/100` is something we think will happen.** A claim, not a
 *     measurement.
 *   - **`64%` is something that did happen.** A hit rate, a calibration bucket,
 *     a share of a real sample.
 *
 * This was almost the pattern already, by accident: the board, the timeline and
 * the slips used one, the record and referee pages used the other, and the
 * explorer and character pages used both. Making it a rule costs nothing and
 * tells a reader at a glance whether they are looking at a prediction or a
 * result.
 *
 * The rule governs NUMBERS IN THE INTERFACE: a cell, a badge, a metric. Running
 * prose is exempt, because a character saying "64% says one foul" is speaking,
 * and "64/100 says one foul" is a spreadsheet talking.
 */
export function forecast(probability: number): string {
  return `${Math.round(probability * 100)}/100`;
}

/** An observed share of a real sample. See `forecast` for when to use which. */
export function observed(share: number, places = 0): string {
  return `${(share * 100).toFixed(places)}%`;
}
