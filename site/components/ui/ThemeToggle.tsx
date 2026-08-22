"use client";

/**
 * Light, dark, or follow the system.
 *
 * The site respected `prefers-color-scheme` and offered no way to override it,
 * which is fine until someone runs a dark desktop and wants to read a dense
 * table in daylight. Three states rather than two, because "follow the system"
 * is a real preference and collapsing it into a boolean loses it.
 *
 * The choice is written to localStorage and applied by an inline script in the
 * document head, before first paint. Applying it here instead would show the
 * wrong theme for a frame on every load.
 */

import { useEffect, useState } from "react";
import s from "./rail.module.css";

type Theme = "light" | "dark" | "system";

const ORDER: Theme[] = ["system", "light", "dark"];

const LABEL: Record<Theme, string> = {
  system: "Match system",
  light: "Light",
  dark: "Dark",
};

export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("system");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    try {
      const stored = localStorage.getItem("theme") as Theme | null;
      if (stored && ORDER.includes(stored)) setTheme(stored);
    } catch {
      // Private browsing, or site data blocked. The default is correct anyway.
    }
    setReady(true);
  }, []);

  function choose(next: Theme) {
    setTheme(next);
    const root = document.documentElement;
    if (next === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", next);
    try {
      localStorage.setItem("theme", next);
    } catch {
      // Nothing to do. The choice still applies for this page view.
    }
  }

  const next = ORDER[(ORDER.indexOf(theme) + 1) % ORDER.length];

  return (
    <button
      type="button"
      className={s.theme}
      onClick={() => choose(next)}
      // Before the stored value is read, the label would claim a state we have
      // not confirmed. Hiding it from screen readers for that frame is honest.
      aria-hidden={!ready}
      aria-label={`Theme: ${LABEL[theme]}. Switch to ${LABEL[next]}.`}
      title={`Theme: ${LABEL[theme]}`}
    >
      <Icon theme={theme} />
    </button>
  );
}

function Icon({ theme }: { theme: Theme }) {
  if (theme === "light") {
    return (
      <svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.5">
        <circle cx="10" cy="10" r="3.5" />
        <path d="M10 2v2M10 16v2M2 10h2M16 10h2M4.3 4.3l1.4 1.4M14.3 14.3l1.4 1.4M15.7 4.3l-1.4 1.4M5.7 14.3l-1.4 1.4" strokeLinecap="round" />
      </svg>
    );
  }
  if (theme === "dark") {
    return (
      <svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M16 11.5A6.5 6.5 0 0 1 8.5 4a6.5 6.5 0 1 0 7.5 7.5Z" strokeLinejoin="round" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.5">
      <rect x="2.5" y="4" width="15" height="10" rx="1.5" />
      <path d="M7 17h6" strokeLinecap="round" />
    </svg>
  );
}
