"use client";

/**
 * The slip rail: the competitors' slips hang from a wire, pegged by square
 * clips, and swing like the physics says they should (lib/pendulum, ported
 * from the ENVRT passport rail). Scroll or flick the rail and every slip
 * trails and settles; pull one DOWN and it tears off at the perforation and
 * expands into a focused view for proper reading. Clicking does the same
 * without the ceremony. Reduced motion gets the plain grid and a plain
 * click, no physics anywhere.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useMotionValue, useAnimationFrame, useReducedMotion, type MotionValue } from "framer-motion";
import type { Bet, SlateShape } from "@/lib/data";
import type { Outcomes } from "@/lib/graded";
import {
  cssRotationFor,
  driveFromLag,
  stepPendulum,
  type LagState,
  type PendulumState,
} from "@/lib/pendulum";
import Bets, { SlipCard, type SlipCharacter } from "./Bets";
import s from "./sliprail.module.css";

/** Pivot to centre of mass, px. Sets the swing period; taste, not physics. */
const LENGTH = 130;
/** How far a slip travels down before it tears off the rail. */
const TEAR_PX = 64;

export default function SlipRail(props: {
  bets: Record<string, Record<string, Bet>>;
  characters: SlipCharacter[];
  shapes: SlateShape[];
  outcomes?: Outcomes;
  gameOver?: boolean;
}) {
  const reduced = useReducedMotion();
  if (reduced) return <Bets {...props} />;
  return <Rail {...props} />;
}

function Rail({
  bets,
  characters,
  shapes,
  outcomes,
  gameOver = false,
}: {
  bets: Record<string, Record<string, Bet>>;
  characters: SlipCharacter[];
  shapes: SlateShape[];
  outcomes?: Outcomes;
  gameOver?: boolean;
}) {
  const hung = characters.filter((ch) => bets[ch.id]);
  const scrollerRef = useRef<HTMLDivElement>(null);
  const lagRef = useRef<LagState | null>(null);
  const statesRef = useRef<PendulumState[]>(hung.map(() => ({ theta: 0, omega: 0 })));
  const rotates = useRef<MotionValue<number>[]>([]);
  const [open, setOpen] = useState<string | null>(null);

  useAnimationFrame((_, delta) => {
    const scroller = scrollerRef.current;
    if (!scroller) return;
    const dt = Math.min(delta / 1000, 1 / 20);
    if (dt <= 0) return;
    // The pivot is the content: scrolling right moves it left under the
    // slips, so the rail's travel is the negative of scrollLeft.
    const position = -scroller.scrollLeft;
    if (!lagRef.current) lagRef.current = { fast: position, slow: position };
    const { lag, drive } = driveFromLag(lagRef.current, position, dt);
    lagRef.current = lag;
    statesRef.current = statesRef.current.map((state, i) => {
      const next = stepPendulum(state, dt, drive, LENGTH);
      rotates.current[i]?.set(cssRotationFor(next.theta));
      return next;
    });
  });

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
      <div ref={scrollerRef} className={s.scroller}>
        <div className={s.track}>
          {hung.map((ch, i) => (
            <Hanger
              key={ch.id}
              index={i}
              rotates={rotates}
              onOpen={() => setOpen(ch.id)}
            >
              <SlipCard
                character={ch}
                own={bets[ch.id]}
                shapes={shapes}
                outcomes={outcomes}
                gameOver={gameOver}
              />
            </Hanger>
          ))}
        </div>
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
              />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

function Hanger({
  index,
  rotates,
  onOpen,
  children,
}: {
  index: number;
  rotates: React.MutableRefObject<MotionValue<number>[]>;
  onOpen: () => void;
  children: React.ReactNode;
}) {
  const rotate = useMotionValue(0);
  rotates.current[index] = rotate;
  const [gripped, setGripped] = useState(false);

  return (
    <motion.div className={s.hanger} style={{ rotate }}>
      <span className={gripped ? `${s.clip} ${s.clipGripped}` : s.clip} aria-hidden />
      <motion.div
        className={s.sheet}
        drag="y"
        dragConstraints={{ top: 0, bottom: TEAR_PX + 26 }}
        dragElastic={0.06}
        dragSnapToOrigin
        onDragStart={() => setGripped(true)}
        onDragEnd={(_, info) => {
          setGripped(false);
          if (info.offset.y > TEAR_PX || info.velocity.y > 620) onOpen();
        }}
        onTap={onOpen}
        whileDrag={{ cursor: "grabbing" }}
      >
        {children}
      </motion.div>
    </motion.div>
  );
}
