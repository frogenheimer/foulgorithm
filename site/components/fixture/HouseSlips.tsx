"use client";

/**
 * The house's three slips, safe to rogue, in the eleven's receipt format.
 *
 * Three SlipCards, one per tier, so house and models read as the same kind
 * of thing (docs/45). The reader chooses the paper (docs/47): a bookie's
 * slip by default, a thermal receipt or a boarding pass, remembered in this
 * browser. Nothing here is selected on the page: the slips are built in the
 * pipeline from the house's own numbers and the recipes.
 */

import { useEffect, useState } from "react";
import type { Bet, SlateShape } from "@/lib/data";
import type { Outcomes } from "@/lib/graded";
import { SlipCard, type SlipVariant } from "@/components/five/Bets";
import { Toggle } from "@/components/kit";
import s from "./houseslips.module.css";

const TIERS: { key: string; label: string }[] = [
  { key: "safe", label: "Safe" },
  { key: "optimistic", label: "Optimistic" },
  { key: "rogue", label: "Rogue" },
];

const STORAGE = "foulgorithm.slipStyle";
const STYLES: { value: SlipVariant; label: string }[] = [
  { value: "slip", label: "Bookie\u2019s slip" },
  { value: "receipt", label: "Receipt" },
  { value: "ticket", label: "Boarding pass" },
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
  const [style, setStyle] = useState<SlipVariant>("slip");
  useEffect(() => {
    try {
      const held = window.localStorage.getItem(STORAGE) as SlipVariant | null;
      if (held && STYLES.some((o) => o.value === held)) setStyle(held);
    } catch {
      /* private mode or blocked storage: the default stands */
    }
  }, []);
  const choose = (v: SlipVariant) => {
    setStyle(v);
    try {
      window.localStorage.setItem(STORAGE, v);
    } catch {
      /* remembered for this page only */
    }
  };

  return (
    <div className={s.wrap}>
      <Toggle value={style} options={STYLES} onChange={choose} label="Slip style" />
      <div className={s.row}>
        {TIERS.map((t) => {
          const shape = shapes.find((sh) => sh.key === t.key) ?? { key: t.key, label: t.label };
          return (
            <SlipCard
              key={t.key}
              character={{ id: "house", name: `The house \u00b7 ${t.label}` }}
              own={{ [t.key]: slips[t.key] ?? null }}
              shapes={[shape]}
              outcomes={outcomes}
              gameOver={gameOver}
              variant={style}
            />
          );
        })}
      </div>
    </div>
  );
}
