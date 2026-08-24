/**
 * The explorer's cap: top rows only, until the reader asks for the rest.
 * An active search always bypasses the cap, because searching inside the
 * visible ten would hide the very row the reader typed a name to find.
 */

export function capped<T>(
  rows: T[],
  cap: number | undefined,
  showAll: boolean,
  searching: boolean
): T[] {
  return cap && !showAll && !searching ? rows.slice(0, cap) : rows;
}
