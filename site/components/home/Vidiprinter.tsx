"use client";

/**
 * The vidiprinter as one line (docs/50).
 *
 * One row that changes: every bet that landed, newest game first, then the
 * misses, each sliding up into the row, holding, and sliding out as the next
 * arrives. A disclosure at the end of the row opens the whole feed in the
 * same order. A reader who asked for reduced motion gets the line changing
 * on the same clock without the slide.
 */

import { useEffect, useState } from "react";
import { orderForTicker, type PrinterLine } from "@/lib/vidiprinter";
import s from "./vidiprinter.module.css";

/** How long a verdict holds before the next one comes in. */
const HOLD_MS = 4000;
/** The slide out, matched to the keyframes in the stylesheet. */
const LEAVE_MS = 380;

export default function Vidiprinter({ lines }: { lines: PrinterLine[] }) {
  const ordered = orderForTicker(lines);
  const [at, setAt] = useState(0);
  const [leaving, setLeaving] = useState(false);
  const [still, setStill] = useState(false);

  useEffect(() => {
    setStill(window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }, []);

  useEffect(() => {
    if (ordered.length < 2) return;
    let leave: ReturnType<typeof setTimeout> | undefined;
    const hold = setInterval(() => {
      if (still) {
        setAt((n) => (n + 1) % ordered.length);
        return;
      }
      setLeaving(true);
      leave = setTimeout(() => {
        setAt((n) => (n + 1) % ordered.length);
        setLeaving(false);
      }, LEAVE_MS);
    }, HOLD_MS);
    return () => {
      clearInterval(hold);
      if (leave) clearTimeout(leave);
    };
  }, [ordered.length, still]);

  if (ordered.length === 0) return null;
  const current = ordered[at % ordered.length];
  const motion = still ? "" : leaving ? s.leaving : s.entering;

  return (
    <div className={s.printer}>
      <div className={s.row} role="status" aria-live="polite" aria-label="Vidiprinter">
        <span className={s.kicker} aria-hidden>
          Vidiprinter
        </span>
        <span className={s.stage}>
          <span
            key={`${at}-${current.text}`}
            className={`${s.line} ${current.tone === "won" ? s.won : s.lost} ${motion}`}
          >
            {current.text}
          </span>
        </span>
        <details className={s.report}>
          <summary className={s.reportHead}>Full report · {ordered.length}</summary>
          <ol className={s.reportList} aria-label="Every settled bet">
            {ordered.map((line, i) => (
              <li key={i} className={line.tone === "won" ? s.won : s.lost}>
                {line.text}
              </li>
            ))}
          </ol>
        </details>
      </div>
    </div>
  );
}
