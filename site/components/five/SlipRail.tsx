"use client";

/**
 * The slip rail, second cut: a contained carousel in the ENVRT manner.
 *
 * The wire holds paper slips, real paper whatever the theme, each hung
 * through a punched hole on a square peg with a ragged tear-off bottom.
 * The rail drifts slowly on its own, pauses the moment a pointer arrives,
 * drags with momentum, and every slip trails and settles on the ported
 * pendulum (lib/pendulum, from the ENVRT passport rail). Pull a slip down
 * and it tears off at the perforation into a focused reading view; a plain
 * click does the same. Reduced motion gets the grid and a click.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import {
  AnimatePresence,
  motion,
  useMotionValue,
  useAnimationFrame,
  useReducedMotion,
  type MotionValue,
} from "framer-motion";
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
/** Ambient drift, px/s. Slow enough to read; pauses under any pointer. */
const DRIFT = 14;

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
  return <Rail {...props} />;
}

function Rail({ bets, characters, shapes, outcomes, gameOver = false, medals }: RailProps) {
  const hung = characters.filter((ch) => bets[ch.id]);
  const frameRef = useRef<HTMLDivElement>(null);
  const trackRef = useRef<HTMLDivElement>(null);
  const x = useMotionValue(0);
  const lagRef = useRef<LagState | null>(null);
  const statesRef = useRef<PendulumState[]>(hung.map(() => ({ theta: 0, omega: 0 })));
  const rotates = useRef<MotionValue<number>[]>([]);
  const restingRef = useRef(true);
  const driftDir = useRef(-1);
  const [range, setRange] = useState(0);
  const [open, setOpen] = useState<string | null>(null);

  // The drag range: how far the track may travel inside its frame.
  useEffect(() => {
    const measure = () => {
      const frame = frameRef.current;
      const track = trackRef.current;
      if (!frame || !track) return;
      setRange(Math.max(0, track.scrollWidth - frame.clientWidth));
    };
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, [hung.length]);

  useAnimationFrame((_, delta) => {
    const dt = Math.min(delta / 1000, 1 / 20);
    if (dt <= 0) return;

    // The drift: the wire wanders until a pointer claims it, ping-ponging
    // at the ends so the whole set passes a patient reader.
    if (restingRef.current && range > 0) {
      let next = x.get() + driftDir.current * DRIFT * dt;
      if (next < -range) {
        next = -range;
        driftDir.current = 1;
      } else if (next > 0) {
        next = 0;
        driftDir.current = -1;
      }
      x.set(next);
    }

    const position = x.get();
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
      <div
        ref={frameRef}
        className={s.frame}
        onPointerEnter={() => (restingRef.current = false)}
        onPointerLeave={() => (restingRef.current = true)}
      >
        <span className={s.wire} aria-hidden />
        <motion.div
          ref={trackRef}
          className={s.track}
          style={{ x }}
          drag="x"
          dragConstraints={{ left: -range, right: 0 }}
          dragElastic={0.06}
        >
          {hung.map((ch, i) => (
            <Hanger key={ch.id} index={i} rotates={rotates} onOpen={() => setOpen(ch.id)}>
              <SlipCard
                character={ch}
                own={bets[ch.id]}
                shapes={shapes}
                outcomes={outcomes}
                gameOver={gameOver}
                medal={medals?.[ch.id]}
              />
            </Hanger>
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
      <span className={gripped ? `${s.peg} ${s.pegGripped}` : s.peg} aria-hidden />
      <motion.div
        className={s.paper}
        drag="y"
        dragPropagation
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
        <span className={s.hole} aria-hidden />
        {children}
        <span className={s.barcode} aria-hidden />
      </motion.div>
    </motion.div>
  );
}
