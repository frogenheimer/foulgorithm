"use client";

/**
 * A YouTube short that drifts around the screen like the old DVD-player
 * idle logo, on pages about Arsenal only. Oliver's, 29 August 2026.
 *
 * Honest costs: the embed loads YouTube's player, and autoplay is only
 * allowed muted. So it is lazy, muted, dismissable (remembered for the
 * session), parked still in a corner for anyone who asked for reduced
 * motion, and never rendered for a viewport too narrow to fit it.
 */

import { useEffect, useRef, useState } from "react";
import s from "./bouncingshort.module.css";

const VIDEO = "thJjDcikJ7A";
const DISMISSED = "foulgorithm.shortDismissed";
const SPEED = 1.6;

export default function BouncingShort() {
  const [show, setShow] = useState(false);
  const [still, setStill] = useState(false);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    try {
      if (window.sessionStorage.getItem(DISMISSED)) return;
    } catch {
      /* ignore */
    }
    if (window.innerWidth < 720) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    setStill(reduced);
    setShow(true);
  }, []);

  useEffect(() => {
    if (!show || still) return;
    const el = box.current;
    if (!el) return;
    let x = 40;
    let y = 80;
    let dx = SPEED;
    let dy = SPEED;
    let raf = 0;
    const step = () => {
      const w = el.offsetWidth;
      const h = el.offsetHeight;
      const maxX = window.innerWidth - w;
      const maxY = window.innerHeight - h;
      x += dx;
      y += dy;
      if (x <= 0 || x >= maxX) {
        dx = -dx;
        x = Math.max(0, Math.min(maxX, x));
        el.classList.toggle(s.flash);
      }
      if (y <= 0 || y >= maxY) {
        dy = -dy;
        y = Math.max(0, Math.min(maxY, y));
        el.classList.toggle(s.flash);
      }
      el.style.transform = `translate(${x}px, ${y}px)`;
      raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [show, still]);

  if (!show) return null;
  const dismiss = () => {
    setShow(false);
    try {
      window.sessionStorage.setItem(DISMISSED, "1");
    } catch {
      /* ignore */
    }
  };
  return (
    <div ref={box} className={still ? `${s.box} ${s.parked}` : s.box} aria-label="Arsenal short">
      <button type="button" className={s.close} onClick={dismiss} aria-label="Close the short">
        ×
      </button>
      <iframe
        className={s.frame}
        src={`https://www.youtube.com/embed/${VIDEO}?autoplay=1&mute=1&loop=1&playlist=${VIDEO}&controls=0&playsinline=1`}
        title="Arsenal short"
        loading="lazy"
        allow="autoplay; encrypted-media"
        referrerPolicy="strict-origin-when-cross-origin"
      />
    </div>
  );
}
