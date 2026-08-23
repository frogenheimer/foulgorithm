"use client";

/**
 * Five characters against five odds tiers, for one fixture.
 *
 * The tier is OUR price, and the estimated bookmaker price is derived from it
 * and shown alongside. The other way round is circular: derive the tier from an
 * estimated offer and every combination reads "below fair", because the margin
 * put it there rather than the model finding anything.
 *
 * There is deliberately no value verdict. We have never observed a
 * player-fouls price anywhere, so there is nothing to be good value against.
 * What can honestly be said is how much of a combination the margin eats, and
 * that is shown per cell.
 */

import { useState } from "react";
import type { Slip } from "@/lib/data";
import { MicroLabel } from "@/components/kit";
import s from "./slips.module.css";

const TIERS = ["2/1", "3/1", "5/1", "10/1", "20/1"];

export default function SlipGrid({
  slips,
  characters,
  names,
}: {
  slips: Record<string, Slip[]>;
  characters: string[];
  /** id -> name as written, so the table does not capitalise ids in CSS. */
  names?: Record<string, string>;
}) {
  const [open, setOpen] = useState<string | null>(null);
  const present = characters.filter((c) => slips[c]?.length);
  if (!present.length) return null;

  // Two readings, and they are opposites. Boldest is the biggest disagreement
  // with the other four; leanest reaches the same tier in the fewest legs,
  // which means the least margin eaten. Neither is "the pick".
  let boldest: { cid: string; slip: Slip; gap: number } | null = null;
  let leanest: { cid: string; slip: Slip } | null = null;
  for (const cid of present) {
    for (const slip of slips[cid]) {
      const gap =
        slip.legs.reduce((a, l) => a + (l.prob - l.packProb), 0) / slip.legs.length;
      if (!boldest || gap > boldest.gap) boldest = { cid, slip, gap };
      if (slip.targetLabel === "2/1") {
        if (!leanest || slip.legCount < leanest.slip.legCount) leanest = { cid, slip };
      }
    }
  }

  return (
    <div className={s.wrap}>
      <div className={s.scroll}>
        <table className={s.grid}> {/* audit-ignore B7: matrix with expandable rows; DataTable has no expand support yet and the explorer needs the same */}
          <thead>
            <tr>
              <th scope="col" style={{ textAlign: "left" }}>
                Character
              </th>
              {TIERS.map((t) => (
                <th key={t} scope="col">
                  {t}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {present.map((cid) => {
              const ladder = slips[cid];
              const rowOpen = open?.startsWith(`${cid}|`);
              const openSlip = rowOpen
                ? ladder.find((x) => `${cid}|${x.targetLabel}` === open)
                : undefined;
              return (
                <>
                  <tr key={cid} style={{ ["--char" as string]: `var(--ch-${cid})` }}>
                    <td>
                      <span className={s.who}>
                        <span className={s.swatch} aria-hidden />
                        <span className={s.name}>{names?.[cid] ?? cid}</span>
                      </span>
                    </td>
                    {TIERS.map((label) => {
                      const slip = ladder.find((x) => x.targetLabel === label);
                      if (!slip) return <td key={label}>&mdash;</td>;
                      const id = `${cid}|${label}`;
                      return (
                        <td key={label}>
                          <button
                            type="button"
                            className={open === id ? s.cellOn : s.cell}
                            onClick={() => setOpen(open === id ? null : id)}
                            aria-expanded={open === id}
                          >
                            <span className={s.price}>{slip.actualOdds.toFixed(2)}</span>
                            <span className={s.sub}>
                              {slip.outOf100}/100 · {slip.legCount} legs
                            </span>
                          </button>
                        </td>
                      );
                    })}
                  </tr>
                  {openSlip && (
                    <tr key={`${cid}-legs`} className={s.legsRow}>
                      <td colSpan={TIERS.length + 1}>
                        <Legs slip={openSlip} />
                      </td>
                    </tr>
                  )}
                </>
              );
            })}
          </tbody>
        </table>
      </div>

      {(boldest || leanest) && (
        <div className={s.picks}>
          {boldest && (
            <article
              className={s.pick}
              style={{ ["--char" as string]: `var(--ch-${boldest.cid})` }}
            >
              <MicroLabel>Boldest read</MicroLabel>
              <strong style={{ textTransform: "capitalize" }}>
                {boldest.cid} · {boldest.slip.targetLabel}
              </strong>
              <p className={s.pickWhy}>
                Sits {Math.round(boldest.gap * 100)} points clear of what the other four
                say about the same legs. The biggest disagreement on the board, which
                makes it the most interesting and the most likely to be wrong.
              </p>
            </article>
          )}
          {leanest && (
            <article
              className={s.pick}
              style={{ ["--char" as string]: `var(--ch-${leanest.cid})` }}
            >
              <MicroLabel>Least margin lost</MicroLabel>
              <strong style={{ textTransform: "capitalize" }}>
                {leanest.cid} · {leanest.slip.targetLabel}
              </strong>
              <p className={s.pickWhy}>
                Reaches the tier in {leanest.slip.legCount} legs, so a bookmaker&apos;s
                margin takes {Math.round(leanest.slip.takeOut * 100)}% rather than the
                40-odd percent a longer combination loses. Fewer legs is structurally the
                better bet at the same risk.
              </p>
            </article>
          )}
        </div>
      )}

      <p className={s.caveat}>
        The tier is <strong>our</strong> price. The offered price is an estimate: no
        player-fouls price has ever been published anywhere we can reach, so it assumes a
        15% bookmaker margin per leg, compounding. That compounding is the reason
        accumulators get pushed, and it is why no combination here carries a value
        verdict. There is nothing observed to be good value against.
      </p>
    </div>
  );
}

function Legs({ slip }: { slip: Slip }) {
  return (
    <div className={s.legs}>
      <ul className={s.legList}>
        {slip.legs.map((l) => (
          <li key={l.player + l.market} className={s.leg}>
            <span className={s.legPlayer}>{l.player}</span>
            <span className={s.legWhat}>
              {l.fouls}+ {l.market === "drawn" ? "fouls won" : "fouls"}
              {l.thin && " · thin evidence"}
            </span>
            <span className={s.legProb}>
              {l.outOf100}/100
            </span>
            {l.reason && <p className={s.legReason}>{l.reason}</p>}
          </li>
        ))}
      </ul>
      <div className={s.maths}>
        <div className={s.mathsItem}>
          <MicroLabel>We make it</MicroLabel>
          <span className={s.mathsValue}>{slip.actualOdds.toFixed(2)}</span>
        </div>
        <div className={s.mathsItem}>
          <MicroLabel>Likely offered</MicroLabel>
          <span className={s.mathsValue}>{slip.estimatedOffer.toFixed(2)}</span>
        </div>
        <div className={s.mathsItem}>
          <MicroLabel>Margin takes</MicroLabel>
          <span className={s.mathsValue}>{Math.round(slip.takeOut * 100)}%</span>
        </div>
        <div className={s.mathsItem}>
          <MicroLabel>Worth taking above</MicroLabel>
          <span className={s.mathsValue}>{slip.floor.toFixed(2)}</span>
        </div>
      </div>
    </div>
  );
}
