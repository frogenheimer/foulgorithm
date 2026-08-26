"use client";

/**
 * Players or Teams.
 *
 * Players leads, because it is what a reader came for: the team record tells
 * you how two clubs behave in general, and the eleven tells you who is
 * actually going to give the fouls away tonight.
 *
 * Client-side only for the switch. Both panels are rendered by the server and
 * passed in, so nothing about the data reaches the browser twice and the tab
 * costs a class name rather than a fetch.
 */

import { useState } from "react";
import type { ReactNode } from "react";
import { Toggle } from "@/components/kit";
import s from "./stats.module.css";

type Tab = "players" | "teams";

export default function TieTabs({
  players,
  teams,
}: {
  players: ReactNode;
  teams: ReactNode;
}) {
  const [tab, setTab] = useState<Tab>("players");

  return (
    <div className="stack">
      <Toggle<Tab>
        value={tab}
        label="What to show"
        onChange={setTab}
        options={[
          { value: "players", label: "Players" },
          { value: "teams", label: "Teams" },
        ]}
      />
      {/* Both panels stay mounted so switching back does not re-render a long
          table, and the hidden one is taken out of the accessibility tree
          rather than merely moved off screen. */}
      <div hidden={tab !== "players"}>{players}</div>
      <div hidden={tab !== "teams"}>{teams}</div>
    </div>
  );
}
