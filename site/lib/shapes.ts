/**
 * Which shapes a set of bets was built to.
 *
 * The payload's `slates.shapes` describes the CURRENT contract. A page from
 * before a contract change (the 29 August 2026 switch from shapes to
 * foul-event tiers) still has to render its own bets, so an archived slice
 * carries the shapes it was published with, and failing that the shapes are
 * read off the bets themselves: their keys and labels are all a slip needs.
 */

import type { Bet, SlateShape } from "./data";

export function shapesFor(
  bets: Record<string, Record<string, Bet>> | null | undefined,
  own: SlateShape[] | null | undefined,
  current: SlateShape[]
): SlateShape[] {
  if (own && own.length) return own;
  const keys = new Set<string>();
  const labels = new Map<string, string>();
  for (const byKey of Object.values(bets ?? {})) {
    for (const [key, bet] of Object.entries(byKey ?? {})) {
      keys.add(key);
      if (bet?.label) labels.set(key, bet.label);
    }
  }
  if (keys.size === 0) return current;
  const currentKeys = new Set(current.map((sh) => sh.key));
  if ([...keys].every((k) => currentKeys.has(k))) return current;
  return [...keys].map((key) => ({ key, label: labels.get(key) ?? key }));
}
