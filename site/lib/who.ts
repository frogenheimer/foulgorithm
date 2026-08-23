/**
 * One identity per player, because three sources spell them three ways.
 *
 * The lineup feed says "Luka Vuskovic", the explorer's full name is
 * "Luka Vušković" and its short name is "Vuskovic". Matching on any one of
 * those has failed in three separate places: the opponent factor lost half the
 * league, settlement joined 24 of 1,913 claims, and the pitch put Boscagli on
 * it three times because the dropdown offered a short name where the slot held
 * a long one.
 *
 * Everything on a pitch keys off `who()`. Nothing keys off a display string.
 */

/** Lowercase, accents stripped, punctuation dropped. */
export function who(name: string): string {
  return name
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9 ]/g, "")
    .trim();
}

/**
 * Match a name from one source against rows from another.
 *
 * Tries the full name, then the short name, then the surname. Surname alone is
 * the last resort and only when it is unique in the squad: matching on it
 * freely is how Danny Ward the goalkeeper inherits Danny Ward the striker's
 * record.
 */
export function findPlayer<T extends { player: string; fullName: string }>(
  rows: T[],
  name: string
): T | undefined {
  const key = who(name);
  const exact = rows.find((r) => who(r.fullName) === key || who(r.player) === key);
  if (exact) return exact;

  const surname = key.split(" ").pop() ?? key;
  const bySurname = rows.filter(
    (r) => who(r.player) === surname || who(r.fullName).split(" ").pop() === surname
  );
  return bySurname.length === 1 ? bySurname[0] : undefined;
}
