/**
 * The fixture page shows the top of the player table, not all of it: forty
 * rows of every substitute goalkeeper buried the sections below. The cap has
 * one rule worth pinning: a reader who searches must always see their result,
 * so an active search bypasses the cap entirely rather than searching inside
 * the visible ten.
 */

import { describe, expect, it } from "vitest";
import { capped } from "./explorer";

const ROWS = Array.from({ length: 40 }, (_, i) => `p${i}`);

describe("capped", () => {
  it("shows only the top of the table until the reader asks for the rest", () => {
    expect(capped(ROWS, 10, false, false)).toHaveLength(10);
    expect(capped(ROWS, 10, true, false)).toHaveLength(40);
  });

  it("never hides a search result behind the cap", () => {
    expect(capped(ROWS, 10, false, true)).toHaveLength(40);
  });

  it("leaves the table alone when no cap is asked for", () => {
    expect(capped(ROWS, undefined, false, false)).toHaveLength(40);
  });
});
