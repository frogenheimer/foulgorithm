"use client";

/**
 * The teletype. Lines arrive character by character, the way scores used to
 * on a Saturday afternoon; a reader who asked for reduced motion gets the
 * finished feed instantly. The words carry the verdicts; the tint only makes
 * them findable.
 */

import { useEffect, useState } from "react";
import type { PrinterLine } from "@/lib/vidiprinter";
import s from "./vidiprinter.module.css";

const CHARS_PER_TICK = 2;
const TICK_MS = 24;

export default function Vidiprinter({ lines }: { lines: PrinterLine[] }) {
  const total = lines.reduce((n, l) => n + l.text.length, 0);
  const [shown, setShown] = useState(0);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setShown(total);
      return;
    }
    const timer = setInterval(() => {
      setShown((n) => {
        if (n >= total) {
          clearInterval(timer);
          return n;
        }
        return n + CHARS_PER_TICK;
      });
    }, TICK_MS);
    return () => clearInterval(timer);
  }, [total]);

  let budget = shown;
  return (
    <div className={s.printer} role="log" aria-label="Settled bets">
      {lines.map((line, i) => {
        const take = Math.max(0, Math.min(line.text.length, budget));
        budget -= line.text.length;
        if (take === 0) return null;
        return (
          <div key={i} className={line.tone === "won" ? s.won : s.lost}>
            {line.text.slice(0, take)}
            {take < line.text.length && <span className={s.cursor} aria-hidden />}
          </div>
        );
      })}
    </div>
  );
}
