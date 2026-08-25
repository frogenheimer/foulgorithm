/**
 * The physics that swings the slips, sanity-pinned at the port boundary.
 * Three facts the rail depends on: a rail moving at constant speed settles
 * the slips (steady drift produces bounded, decaying motion, not a wind-up),
 * no throw ever folds a slip past the angle limit, and the CSS rotation is
 * the mirror of the physics angle, because a mirrored trailing tag is an
 * accurately simulated LEADING tag and looks wrong in the one way nothing
 * physical does.
 */

import { describe, expect, it } from "vitest";
import { PENDULUM, cssRotationFor, damp, stepPendulum } from "./pendulum";

describe("stepPendulum", () => {
  it("a hard constant drive settles at a lean, never a wind-up", () => {
    let state = { theta: 0, omega: 0 };
    for (let i = 0; i < 600; i++) state = stepPendulum(state, 1 / 60, 1200, 120);
    const settled = state.theta;
    for (let i = 0; i < 60; i++) state = stepPendulum(state, 1 / 60, 1200, 120);
    expect(Math.abs(state.theta - settled)).toBeLessThan(0.02);
    expect(Math.abs(settled)).toBeLessThan(PENDULUM.MAX_ANGLE + 1e-9);
  });

  it("no throw folds a slip past the angle limit", () => {
    let state = { theta: 0, omega: 12 };
    for (let i = 0; i < 240; i++) state = stepPendulum(state, 1 / 60, 50000, 120);
    expect(Math.abs(state.theta)).toBeLessThanOrEqual(PENDULUM.MAX_ANGLE + 1e-9);
  });

  it("released, it rings down towards vertical", () => {
    let state = { theta: 0.3, omega: 0 };
    for (let i = 0; i < 900; i++) state = stepPendulum(state, 1 / 60, 0, 120);
    expect(Math.abs(state.theta)).toBeLessThan(0.02);
  });
});

describe("cssRotationFor", () => {
  it("mirrors the physics angle, so tags trail instead of lead", () => {
    expect(cssRotationFor(0.1)).toBeLessThan(0);
  });
});

describe("damp", () => {
  it("is frame-rate independent: two small steps equal one big one, closely", () => {
    const one = damp(0, 100, 0.1, 0.032);
    let two = damp(0, 100, 0.1, 0.016);
    two = damp(two, 100, 0.1, 0.016);
    expect(Math.abs(one - two)).toBeLessThan(0.5);
  });
});
