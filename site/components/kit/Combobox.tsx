"use client";

/**
 * A searchable select.
 *
 * A native `<select>` is fine for five options and hostile for forty: on a
 * squad list you cannot type, cannot see who is suggested, and on mobile it
 * becomes a full-screen wheel of names.
 *
 * Options can carry a `group`, and grouped options sort to the top. On a pitch
 * that means the players who actually play the position are offered first, and
 * everyone else is still one keystroke away rather than hidden.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import s from "./kit.module.css";

export type Option = {
  value: string;
  label: string;
  /** Shown right-aligned. A rate, a shirt number, anything short. */
  meta?: string;
  /** Options carrying a group are offered before the rest, under its heading. */
  group?: string;
};

export function Combobox({
  value,
  options,
  onChange,
  label,
  placeholder = "Search",
  restLabel = "Everyone else",
}: {
  value: string;
  options: Option[];
  onChange: (value: string) => void;
  label: string;
  placeholder?: string;
  restLabel?: string;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function away(e: MouseEvent) {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", away);
    return () => document.removeEventListener("mousedown", away);
  }, [open]);

  const { suggested, rest } = useMemo(() => {
    const q = query.trim().toLowerCase();
    const matches = options.filter((o) => !q || o.label.toLowerCase().includes(q));
    return {
      suggested: matches.filter((o) => o.group),
      rest: matches.filter((o) => !o.group),
    };
  }, [options, query]);

  const groupName = suggested[0]?.group;

  function pick(v: string) {
    onChange(v);
    setQuery("");
    setOpen(false);
  }

  return (
    <div className={s.combo} ref={box}>
      <input
        className={s.comboInput}
        value={open ? query : value}
        placeholder={open ? placeholder : undefined}
        aria-label={label}
        role="combobox"
        aria-expanded={open}
        onFocus={() => {
          setOpen(true);
          setQuery("");
        }}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Escape") setOpen(false);
          if (e.key === "Enter") {
            const first = suggested[0] ?? rest[0];
            if (first) pick(first.value);
          }
        }}
      />

      {open && (
        <ul className={s.comboList} role="listbox" aria-label={label}>
          {suggested.length > 0 && (
            <>
              {groupName && <li className={s.comboGroup}>{groupName}</li>}
              {suggested.map((o) => (
                <li key={o.value}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={o.value === value}
                    className={o.value === value ? s.comboItemOn : s.comboItem}
                    onClick={() => pick(o.value)}
                  >
                    <span>{o.label}</span>
                    {o.meta && <span className={s.comboMeta}>{o.meta}</span>}
                  </button>
                </li>
              ))}
            </>
          )}

          {rest.length > 0 && (
            <>
              {suggested.length > 0 && <li className={s.comboGroup}>{restLabel}</li>}
              {rest.map((o) => (
                <li key={o.value}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={o.value === value}
                    className={o.value === value ? s.comboItemOn : s.comboItem}
                    onClick={() => pick(o.value)}
                  >
                    <span>{o.label}</span>
                    {o.meta && <span className={s.comboMeta}>{o.meta}</span>}
                  </button>
                </li>
              ))}
            </>
          )}

          {suggested.length === 0 && rest.length === 0 && (
            <li className={s.comboEmpty}>Nobody matches &ldquo;{query}&rdquo;</li>
          )}
        </ul>
      )}
    </div>
  );
}
