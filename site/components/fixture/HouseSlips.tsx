/**
 * The house's three slips, safe to rogue, in the eleven's receipt format.
 *
 * Three SlipCards, one per tier, so house and models read as the same kind
 * of thing (docs/45). Nothing here is selected on the page: the slips are
 * built in the pipeline from the house's own numbers and the recipes.
 */

import type { Bet, SlateShape } from "@/lib/data";
import type { Outcomes } from "@/lib/graded";
import { SlipCard } from "@/components/five/Bets";
import s from "./houseslips.module.css";

const TIERS: { key: string; label: string }[] = [
  { key: "safe", label: "Safe" },
  { key: "optimistic", label: "Optimistic" },
  { key: "rogue", label: "Rogue" },
];

export default function HouseSlips({
  slips,
  shapes,
  outcomes,
  gameOver = false,
}: {
  slips: Record<string, Bet>;
  shapes: SlateShape[];
  outcomes?: Outcomes;
  gameOver?: boolean;
}) {
  return (
    <div className={s.row}>
      {TIERS.map((t) => {
        const shape = shapes.find((sh) => sh.key === t.key) ?? { key: t.key, label: t.label };
        return (
          <SlipCard
            key={t.key}
            character={{ id: "house", name: `The house · ${t.label}` }}
            own={{ [t.key]: slips[t.key] ?? null }}
            shapes={[shape]}
            outcomes={outcomes}
            gameOver={gameOver}
          />
        );
      })}
    </div>
  );
}
