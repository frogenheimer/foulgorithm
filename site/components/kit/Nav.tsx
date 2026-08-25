"use client";

/**
 * 240px, labelled, collapsible to 64px.
 *
 * The previous 64px icon rail was defensible at four destinations and stopped
 * being so at eight: two of the icons were the same bar-chart glyph and nothing
 * told them apart without hovering. Every dashboard worth copying runs 240 to
 * 256px with labels.
 *
 * Grouped, because eight flat destinations is a list and four plus four is a
 * structure. "This round" is what a returning reader wants; the rest is
 * reference they visit once.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import s from "./nav.module.css";

const GROUPS: { label: string; items: { href: string; label: string; icon: ReactNode }[] }[] = [
  {
    label: "This round",
    items: [
      { href: "/", label: "Today", icon: <IconGrid /> },
      { href: "/teams", label: "Teams", icon: <IconShield /> },
    ],
  },
  {
    label: "Reference",
    items: [
      { href: "/characters", label: "The five", icon: <IconUsers /> },
      { href: "/record", label: "Track record", icon: <IconCheck /> },
      { href: "/history", label: "History", icon: <IconTrend /> },
      { href: "/methodology", label: "Methodology", icon: <IconBook /> },
    ],
  },
];

export function Nav({ children, wide = false }: { children: ReactNode; wide?: boolean }) {
  const path = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [theme, setTheme] = useState<"light" | "dark" | "system">("system");
  const navRef = useRef<HTMLElement>(null);

  // The pip: one yellow square that glides to wherever the reader hovers
  // and rests beside the page they are on.
  const [pipTop, setPipTop] = useState<number | null>(null);
  const placePip = useCallback((el: Element | null) => {
    const nav = navRef.current;
    if (!nav || !el) {
      setPipTop(null);
      return;
    }
    const navBox = nav.getBoundingClientRect();
    const box = el.getBoundingClientRect();
    setPipTop(box.top - navBox.top + nav.scrollTop + box.height / 2);
  }, []);
  const pipHome = useCallback(() => {
    placePip(navRef.current?.querySelector('[aria-current="page"]') ?? null);
  }, [placePip]);
  useEffect(() => {
    pipHome();
  }, [path, collapsed, pipHome]);

  // On a phone the nav is a scrolling row and five of the eight destinations
  // start off-screen. At least the one you are on should not.
  useEffect(() => {
    if (!window.matchMedia("(max-width: 860px)").matches) return;
    navRef.current
      ?.querySelector('[aria-current="page"]')
      ?.scrollIntoView({ inline: "center", block: "nearest" });
  }, [path]);

  useEffect(() => {
    try {
      const c = localStorage.getItem("nav-collapsed");
      if (c === "1") setCollapsed(true);
      const t = localStorage.getItem("theme");
      if (t === "light" || t === "dark") setTheme(t);
    } catch {
      // Private browsing, or site data blocked. Defaults are correct anyway.
    }
  }, []);

  function toggleCollapse() {
    const next = !collapsed;
    setCollapsed(next);
    try {
      localStorage.setItem("nav-collapsed", next ? "1" : "0");
    } catch {}
  }

  function cycleTheme() {
    const order = ["system", "light", "dark"] as const;
    const next = order[(order.indexOf(theme) + 1) % order.length];
    setTheme(next);
    const root = document.documentElement;
    if (next === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", next);
    try {
      localStorage.setItem("theme", next);
    } catch {}
  }

  return (
    <div className={wide ? `${s.shell} ${s.wide}` : s.shell}>
      <nav
        ref={navRef}
        className={collapsed ? `${s.nav} ${s.collapsed}` : s.nav}
        aria-label="Primary"
        onMouseLeave={pipHome}
      >
        {pipTop != null && (
          <span
            className={s.pip}
            style={{ transform: `translateY(${Math.round(pipTop)}px)` }}
            aria-hidden
          />
        )}
        <Link href="/" className={s.mark}>
          <span className={s.markGlyph} aria-hidden>
            F
          </span>
          <span className={s.label}>Foulgorithm</span>
        </Link>

        {GROUPS.map((g) => (
          <div key={g.label}>
            <div className={s.group}>{g.label}</div>
            <ul className={s.items}>
              {g.items.map(({ href, label, icon }) => {
                const on = href === "/" ? path === "/" : path.startsWith(href);
                return (
                  <li key={href}>
                    <Link
                      href={href}
                      className={on ? s.itemOn : s.item}
                      aria-current={on ? "page" : undefined}
                      title={collapsed ? label : undefined}
                      onMouseEnter={(e) => placePip(e.currentTarget)}
                    >
                      {icon}
                      <span className={s.label}>{label}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}

        <div className={s.foot}>
          <button
            type="button"
            className={s.iconBtn}
            onClick={cycleTheme}
            aria-label={`Theme: ${theme}. Change it.`}
            title={`Theme: ${theme}`}
          >
            <IconTheme theme={theme} />
          </button>
          <button
            type="button"
            className={s.iconBtn}
            onClick={toggleCollapse}
            aria-label={collapsed ? "Expand navigation" : "Collapse navigation"}
          >
            <IconCollapse collapsed={collapsed} />
          </button>
        </div>
      </nav>

      <div className={s.main}>
        {/* The skip link's landing spot. tabIndex so focus actually moves. */}
        <div className={s.content} id="main" tabIndex={-1}>
          {children}
        </div>
        <footer className={s.footer}>
          <p>
            Every prediction is published before kickoff and graded afterwards, including
            the ones that lose. Prices are what a bet would need to pay to be worth taking,
            not a price anyone is offering.
          </p>
          <p>
            18+. Gambling can be addictive. Free, confidential help from{" "}
            <a href="https://www.begambleaware.org/">BeGambleAware</a> and{" "}
            <a href="https://www.gamcare.org.uk/">GamCare</a>, or self-exclude via{" "}
            <a href="https://www.gamstop.co.uk/">GamStop</a>.
          </p>
        </footer>
      </div>
    </div>
  );
}

/* Icons. Stroke-only, 18px, one weight, each distinguishable from the others at
   a glance, which the previous set was not. */
const P = { fill: "none", stroke: "currentColor", strokeWidth: 1.6, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
const box = { viewBox: "0 0 20 20", width: 18, height: 18 };

function IconGrid() { return <svg {...box} {...P}><rect x="2.5" y="2.5" width="6" height="6" rx="1.2"/><rect x="11.5" y="2.5" width="6" height="6" rx="1.2"/><rect x="2.5" y="11.5" width="6" height="6" rx="1.2"/><rect x="11.5" y="11.5" width="6" height="6" rx="1.2"/></svg>; }
function IconList() { return <svg {...box} {...P}><path d="M7 5h10M7 10h10M7 15h10M3.5 5h.01M3.5 10h.01M3.5 15h.01"/></svg>; }
function IconColumns() { return <svg {...box} {...P}><rect x="2.5" y="3" width="15" height="14" rx="1.5"/><path d="M10 3v14M2.5 7.5h15"/></svg>; }
function IconUsers() { return <svg {...box} {...P}><circle cx="7.5" cy="7" r="2.6"/><path d="M2.8 16.5a4.7 4.7 0 0 1 9.4 0"/><path d="M13.2 5.2a2.6 2.6 0 0 1 0 5M14 12.4a4.7 4.7 0 0 1 3.2 4.1"/></svg>; }
function IconShield() { return <svg {...box} {...P}><path d="M10 2.5 16.5 5v5c0 3.5-2.6 6.4-6.5 7.5C6.1 16.4 3.5 13.5 3.5 10V5z"/></svg>; }
function IconCheck() { return <svg {...box} {...P}><path d="M3 10.5l4 4 10-10"/></svg>; }
function IconTrend() { return <svg {...box} {...P}><path d="M2.5 14.5l5-5 3 3 7-7"/><path d="M13 5.5h4.5V10"/></svg>; }
function IconBook() { return <svg {...box} {...P}><path d="M3 4.5h5a2.5 2.5 0 0 1 2 1 2.5 2.5 0 0 1 2-1h5v11h-5a2.5 2.5 0 0 0-2 1 2.5 2.5 0 0 0-2-1H3z"/><path d="M10 5.5v11"/></svg>; }

function IconTheme({ theme }: { theme: string }) {
  if (theme === "light") return <svg {...box} {...P}><circle cx="10" cy="10" r="3.4"/><path d="M10 2.4v1.8M10 15.8v1.8M2.4 10h1.8M15.8 10h1.8M4.6 4.6l1.3 1.3M14.1 14.1l1.3 1.3M15.4 4.6l-1.3 1.3M5.9 14.1l-1.3 1.3"/></svg>;
  if (theme === "dark") return <svg {...box} {...P}><path d="M16 11.5A6.5 6.5 0 0 1 8.5 4a6.5 6.5 0 1 0 7.5 7.5Z"/></svg>;
  return <svg {...box} {...P}><rect x="2.5" y="4" width="15" height="10" rx="1.5"/><path d="M7 17h6"/></svg>;
}

function IconCollapse({ collapsed }: { collapsed: boolean }) {
  return <svg {...box} {...P}><path d={collapsed ? "M8 5l4 5-4 5" : "M12 5l-4 5 4 5"}/><path d="M16 4v12"/></svg>;
}
