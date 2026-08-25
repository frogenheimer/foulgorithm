"use client";

/**
 * The receipt: third cut, and the one that matches its use case.
 *
 * The competitors' slips print as one continuous receipt, full width of its
 * container, each slip a perforated segment of the same paper. The receipt
 * scrolls plainly: wheel, touch, or grab-and-drag to move faster. No
 * physics, no drift; paper on a spool does not swing. Pulling a segment
 * DOWN rips it off along the perforation into a focused reading view; a
 * plain click does the same. Reduced motion gets the grid and a click.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import {
  AnimatePresence,
  motion,
  useMotionValue,
  useReducedMotion,
} from "framer-motion";
import type { Bet, SlateShape } from "@/lib/data";
import type { Outcomes } from "@/lib/graded";
import Bets, { SlipCard, type SlipCharacter } from "./Bets";
import s from "./sliprail.module.css";

/** How far a segment travels down before it rips off. Deliberate: a
 *  sideways fling that dips should never tear the paper. */
const TEAR_PX = 96;

/** Feed speed of the idle crawl. Slow enough to read a slip as it passes. */
const FEED_PX_PER_S = 14;

type RailProps = {
  bets: Record<string, Record<string, Bet>>;
  characters: SlipCharacter[];
  shapes: SlateShape[];
  outcomes?: Outcomes;
  gameOver?: boolean;
  medals?: Record<string, 1 | 2 | 3>;
};

export default function SlipRail(props: RailProps) {
  const reduced = useReducedMotion();
  if (reduced) return <Bets {...props} />;
  return <Receipt {...props} />;
}

function Receipt({ bets, characters, shapes, outcomes, gameOver = false, medals }: RailProps) {
  const hung = characters.filter((ch) => bets[ch.id]);
  const frameRef = useRef<HTMLDivElement>(null);
  const paperRef = useRef<HTMLDivElement>(null);
  const x = useMotionValue(0);
  const [range, setRange] = useState(0);
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    const measure = () => {
      const frame = frameRef.current;
      const paper = paperRef.current;
      if (!frame || !paper) return;
      setRange(Math.max(0, paper.scrollWidth - frame.clientWidth));
    };
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, [hung.length]);

  // The receipt feeds itself: a slow crawl leftward once it renders, like
  // paper coming off the printer, so a long rail advertises that it scrolls.
  // The FIRST touch of any kind hands control over and the crawl never
  // returns; a feed that fights the reader is worse than no feed.
  const fed = useRef(false);
  useEffect(() => {
    if (range <= 0) return;
    const frame = frameRef.current;
    if (!frame) return;
    let raf = 0;
    let last = performance.now();
    const crawl = (now: number) => {
      const step = ((now - last) / 1000) * FEED_PX_PER_S;
      last = now;
      const next = Math.max(-range, x.get() - step);
      x.set(next);
      if (!fed.current && next > -range) raf = requestAnimationFrame(crawl);
    };
    const stop = () => {
      fed.current = true;
      cancelAnimationFrame(raf);
    };
    if (!fed.current) raf = requestAnimationFrame(crawl);
    frame.addEventListener("pointerdown", stop);
    frame.addEventListener("wheel", stop, { passive: true });
    return () => {
      cancelAnimationFrame(raf);
      frame.removeEventListener("pointerdown", stop);
      frame.removeEventListener("wheel", stop);
    };
  }, [range, x]);

  // Trackpads and wheels scroll the receipt too; the listener is registered
  // by hand because React's onWheel is passive and cannot preventDefault.
  useEffect(() => {
    const frame = frameRef.current;
    if (!frame) return;
    const onWheel = (e: WheelEvent) => {
      const delta = Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : e.deltaY;
      if (delta === 0) return;
      const next = Math.min(0, Math.max(-range, x.get() - delta));
      if (next !== x.get()) {
        x.set(next);
        e.preventDefault();
      }
    };
    frame.addEventListener("wheel", onWheel, { passive: false });
    return () => frame.removeEventListener("wheel", onWheel);
  }, [range, x]);

  const close = useCallback(() => setOpen(null), []);
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, close]);

  const focused = open ? hung.find((ch) => ch.id === open) : null;

  return (
    <>
      <div ref={frameRef} className={s.frame}>
        <motion.div
          ref={paperRef}
          className={s.receipt}
          style={{ x }}
          drag="x"
          dragConstraints={{ left: -range, right: 0 }}
          dragElastic={0.05}
        >
          {hung.map((ch) => (
            <Segment key={ch.id} onOpen={() => setOpen(ch.id)}>
              <SlipCard
                character={ch}
                own={bets[ch.id]}
                shapes={shapes}
                outcomes={outcomes}
                gameOver={gameOver}
                medal={medals?.[ch.id]}
              />
            </Segment>
          ))}
        </motion.div>
      </div>

      <AnimatePresence>
        {focused && (
          <motion.div
            className={s.overlay}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.16 }}
            onClick={close}
            role="dialog"
            aria-modal="true"
            aria-label={`${focused.name}'s slip`}
          >
            <motion.div
              className={s.focus}
              initial={{ y: 28, rotate: 2.5, opacity: 0 }}
              animate={{ y: 0, rotate: 0, opacity: 1 }}
              exit={{ y: 18, opacity: 0 }}
              transition={{ type: "spring", stiffness: 420, damping: 30 }}
              onClick={(e) => e.stopPropagation()}
            >
              <button type="button" className={s.close} onClick={close} autoFocus>
                close
              </button>
              <SlipCard
                character={focused}
                own={bets[focused.id]}
                shapes={shapes}
                outcomes={outcomes}
                gameOver={gameOver}
                medal={medals?.[focused.id]}
              />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

function Segment({ onOpen, children }: { onOpen: () => void; children: React.ReactNode }) {
  return (
    <motion.div
      className={s.segment}
      drag="y"
      dragPropagation
      dragConstraints={{ top: 0, bottom: TEAR_PX + 30 }}
      dragElastic={0.06}
      dragSnapToOrigin
      whileDrag={{ rotate: 1.5, cursor: "grabbing" }}
      onDragEnd={(_, info) => {
        // Downward, dominant and deliberate.
        const dominant = info.offset.y > Math.abs(info.offset.x) * 1.5;
        if (dominant && (info.offset.y > TEAR_PX || info.velocity.y > 900)) onOpen();
      }}
      onTap={onOpen}
    >
      {children}
    </motion.div>
  );
}
