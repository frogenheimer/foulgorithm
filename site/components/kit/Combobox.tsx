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
 *
 * Fully keyboard-driven: arrows move through the list, Enter picks the marked
 * option, Escape closes. The input keeps focus and the marked option travels
 * via aria-activedescendant, which is the combobox pattern screen readers
 * expect; Enter-picks-first-match alone was a dead end for anyone not on a
 * mouse.
 */

import { useEffect, useId, useMemo, useRef, useState } from "react";
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
  trigger,
  onOpenChange,
}: {
  value: string;
  options: Option[];
  onChange: (value: string) => void;
  label: string;
  placeholder?: string;
  restLabel?: string;
  /**
   * Render the closed state yourself. Use this where the current value is
   * already on screen, so the control is a chevron beside it rather than a
   * second copy of the same name.
   */
  trigger?: (open: () => void) => React.ReactNode;
  /** Fires when the list opens or closes, so a caller can raise its own layer. */
  onOpenChange?: (open: boolean) => void;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const box = useRef<HTMLDivElement>(null);
  const baseId = useId();
  const listId = `${baseId}-list`;
  const optionId = (i: number) => `${baseId}-opt-${i}`;

  useEffect(() => {
    if (!open) return;
    function away(e: MouseEvent) {
      if (box.current && !box.current.contains(e.target as Node)) {
        setOpen(false);
        onOpenChange?.(false);
      }
    }
    document.addEventListener("mousedown", away);
    return () => document.removeEventListener("mousedown", away);
  }, [open, onOpenChange]);

  const { suggested, rest } = useMemo(() => {
    const q = query.trim().toLowerCase();
    const matches = options.filter((o) => !q || o.label.toLowerCase().includes(q));
    return {
      suggested: matches.filter((o) => o.group),
      rest: matches.filter((o) => !o.group),
    };
  }, [options, query]);

  const flat = useMemo(() => [...suggested, ...rest], [suggested, rest]);
  const groupName = suggested[0]?.group;

  // The marked option follows the list, not the keystrokes that shaped it.
  useEffect(() => setActive(0), [query, open]);

  useEffect(() => {
    if (!open) return;
    document.getElementById(optionId(active))?.scrollIntoView({ block: "nearest" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, open]);

  function pick(v: string) {
    onChange(v);
    setQuery("");
    setOpen(false);
    onOpenChange?.(false);
  }

  const openIt = () => {
    setOpen(true);
    setQuery("");
    onOpenChange?.(true);
  };

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Escape") {
      setOpen(false);
      onOpenChange?.(false);
      return;
    }
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (!open) return openIt();
      if (flat.length === 0) return;
      const step = e.key === "ArrowDown" ? 1 : -1;
      setActive((a) => (a + step + flat.length) % flat.length);
      return;
    }
    if (e.key === "Enter") {
      const target = flat[active] ?? flat[0];
      if (target) pick(target.value);
    }
  }

  const renderOption = (o: Option, i: number) => (
    <li key={o.value}>
      <button
        type="button"
        id={optionId(i)}
        role="option"
        aria-selected={i === active}
        className={[
          o.value === value ? s.comboItemOn : s.comboItem,
          i === active ? s.comboItemActive : "",
        ]
          .filter(Boolean)
          .join(" ")}
        onMouseMove={() => setActive(i)}
        onClick={() => pick(o.value)}
      >
        <span>{o.label}</span>
        {o.meta && <span className={s.comboMeta}>{o.meta}</span>}
      </button>
    </li>
  );

  return (
    <div className={s.combo} ref={box}>
      {trigger && !open ? (
        trigger(openIt)
      ) : (
        <input
          autoFocus={Boolean(trigger)}
          className={s.comboInput}
          value={open ? query : value}
          placeholder={open ? placeholder : undefined}
          aria-label={label}
          role="combobox"
          aria-haspopup="listbox"
          aria-expanded={open}
          aria-controls={open ? listId : undefined}
          aria-activedescendant={open && flat[active] ? optionId(active) : undefined}
          aria-autocomplete="list"
          onFocus={openIt}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={onKeyDown}
        />
      )}

      {open && (
        <ul className={s.comboList} id={listId} role="listbox" aria-label={label}>
          {suggested.length > 0 && (
            <>
              {groupName && <li className={s.comboGroup}>{groupName}</li>}
              {suggested.map((o, i) => renderOption(o, i))}
            </>
          )}

          {rest.length > 0 && (
            <>
              {suggested.length > 0 && <li className={s.comboGroup}>{restLabel}</li>}
              {rest.map((o, i) => renderOption(o, suggested.length + i))}
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
