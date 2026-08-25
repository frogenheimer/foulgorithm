/**
 * A tag hanging from a wire that somebody is dragging.
 *
 * Ported whole from the ENVRT site's passport rail (src/lib/collective/
 * pendulum.ts, same author), where every constant below earned its comment.
 * Here it swings betting slips instead of passports; the physics does not
 * care.
 *
 * This is a real damped pendulum on a horizontally accelerating pivot, not a
 * rotation keyframe that happens to look like one. The difference shows the
 * moment a user flicks the rail: keyframes carry on at their own pace, a
 * pendulum lurches, overshoots and settles.
 *
 * Equation of motion, from the Lagrangian for a pendulum whose support moves
 * (González, LSU Phys 7221):
 *
 *     θ'' = −(g/L)·sin θ − (A/L)·cos θ − c·θ'
 *
 * θ is measured from straight down and positive θ moves the tag towards +x,
 * that is to the right. A is the pivot's horizontal acceleration.
 *
 * θ is NOT a CSS rotation. An earlier version of this comment claimed it
 * mapped across with no sign flip and that was wrong, which put every tag on
 * the rail leading the drag instead of trailing it. Use cssRotationFor.
 *
 * Three consequences worth knowing before touching the constants:
 *
 * 1. Accelerate the pivot right and the tag swings LEFT. It trails. The
 *    equilibrium is tan θ = −A/g, which is why the term carries a minus.
 *
 * 2. Constant velocity produces no deflection at all. The equation is
 *    unchanged when A = 0, because a pivot at constant speed is just another
 *    inertial frame. A rail scrolling steadily would hold every tag dead
 *    vertical, which looks wrong, and no amount of tuning the pendulum fixes
 *    it because the pendulum is right.
 *
 * 3. g is in px/s² and must be tuned, not borrowed. Real gravity in pixels
 *    swings far too fast. Pick the period, then g = ω²·L.
 *
 * Where the drive comes from is the caller's problem, and it is a problem
 * worth reading driveFromLag below before touching.
 */

export const PENDULUM = {
  /**
   * Tuned so a tag with a typical effective length swings with a period of
   * roughly 0.9s: readable, neither frantic nor sluggish. ω = √(g/L).
   */
  G: 7000,
  /**
   * Damping ratio. Below 0.1 the tag rings for ten seconds, above 0.3 it
   * stops in two swings and reads as stiff. c = 2ζω.
   */
  ZETA: 0.24,
  /**
   * A hard flick reaches several thousand px/s², which the equilibrium angle
   * would turn into 50°+. Tags on a wire do not fold in half, and at 30° the
   * row read as thrashing rather than swinging.
   */
  MAX_ANGLE: 0.32,
  /**
   * Stability bound for the integrator is ω·dt < 2. At ω ≈ 7 this clamp
   * leaves roughly eight times the headroom, and it is the whole answer to
   * variable frame rates and backgrounded tabs.
   */
  MAX_DT: 1 / 30,
} as const;

/**
 * The drive that would hold a tag exactly at MAX_ANGLE, px/s².
 *
 * From tan θ = −A/g, so A = g·tan(θ). Everything the rail produces is
 * squashed below this, which is what stops the angle limit from ever being
 * the thing that stops a tag.
 */
export const DRIVE_AT_MAX_ANGLE = PENDULUM.G * Math.tan(PENDULUM.MAX_ANGLE);

/**
 * Squash a drive smoothly into range instead of clipping it.
 *
 * The previous ceiling was 5000 px/s², more than twice the 2320 needed to
 * reach MAX_ANGLE, so any real flick drove the tags into the angle limit,
 * where the angle is pinned and the angular velocity is zeroed outright. A
 * dozen frames pinned against that wall and then a whip back the other way
 * is what read as "extreme": not a big swing, a discontinuity.
 *
 * tanh is smooth everywhere, approaches the limit without reaching it, and
 * is linear for small inputs, so gentle movement is untouched and only a
 * hard flick feels the compression. The MAX_ANGLE clamp stays as a backstop
 * but should now never fire.
 */
export function saturateDrive(raw: number): number {
  return DRIVE_AT_MAX_ANGLE * Math.tanh(raw / DRIVE_AT_MAX_ANGLE);
}

/**
 * Frame-rate independent exponential approach.
 *
 * `current += (target - current) * 0.2` is the version everyone writes and
 * it is wrong the moment the frame rate moves: at 120Hz it converges twice
 * as fast as at 60Hz, so the same gesture feels different on a newer
 * display. Expressing the rate as a time constant fixes it, and tau is a
 * number with a meaning: about 63% of the way there after tau seconds.
 */
export function damp(current: number, target: number, tau: number, dt: number) {
  return current + (target - current) * (1 - Math.exp(-dt / tau));
}

/**
 * Turn rail movement into a drive, without differentiating twice.
 *
 * This replaces a measured acceleration, and the reason is worth stating
 * because the old version looked reasonable.
 *
 * Acceleration was computed as the frame difference of a smoothed frame
 * difference of position. Two divisions by dt means noise is amplified by
 * 1/dt², so a pixel of hand tremor became 3600 px/s² at 60fps and four
 * times that at 120fps: the animation was measurably worse on a better
 * screen. Worse, the transfer function from position to angle works out at
 * −s²/(L(s² + cs + ω₀²)), whose s² cancels the pendulum's own rolloff, so
 * jitter reached the tags at flat gain at every frequency. The pendulum was
 * providing no filtering at all.
 *
 * Position lag avoids the derivatives entirely, and the reason it works is
 * exact rather than a happy accident. For a one-pole follower with rate α,
 * the lag is
 *
 *     L − f = ((1−α)/α) · (1 − z⁻¹) · H(z) · L
 *
 * where (1 − z⁻¹) is the backward difference, so the lag IS the velocity,
 * already passed through the same low-pass chosen for the smoothing, scaled.
 * The filter comes free and two noisy samples are never subtracted.
 *
 * Two followers rather than the usual one. The common pattern takes raw
 * minus follower, which is a high-pass: at high frequency it passes input
 * jitter at unit gain, and every implementation of it then needs a clamp, a
 * threshold or a ratchet bolted on to cope. Chasing the fast follower with a
 * slow one makes the gap a band-pass instead, so device noise is attenuated
 * before it becomes a signal, and the pendulum's own 1/s² compounds that.
 *
 * It also does the job the air-resistance term used to. Lag is proportional
 * to speed once the rail settles into a steady drift, so the constant-speed
 * lean falls out of the same signal that produces the flick response, and a
 * parameter disappears.
 *
 * This is the pattern behind the widely copied scroll-skew effect and
 * behind GSAP's data-lag: leader minus smoothed follower, scaled.
 */
export const LAG = {
  /** Fast follower time constant, seconds. */
  FAST: 0.045,
  /** Slow follower time constant, seconds. */
  SLOW: 0.18,
  /**
   * px/s² of drive per px of lag. The one knob worth touching, and pure
   * taste rather than physics.
   *
   * A steady 900px/s drag leans the tags about 4.5° here, a hard 4000px/s
   * throw about 15°. For reference the widely copied page-skew version of
   * this pattern lands near 0.8° at the same drag speed, but it is skewing a
   * whole page rather than swinging an object, and a tag that barely moves
   * is not a tag.
   */
  GAIN: 3.5,
} as const;

export interface LagState {
  fast: number;
  slow: number;
}

/**
 * Advance the followers and return the drive they imply.
 *
 * `position` must be the rail's total travel, never a wrapped coordinate.
 * Feeding it a value that jumps by the width of the set every loop would
 * hand every tag a single enormous impulse each time the rail wrapped.
 */
export function driveFromLag(
  lag: LagState,
  position: number,
  dt: number,
): { lag: LagState; drive: number } {
  const fast = damp(lag.fast, position, LAG.FAST, dt);
  const slow = damp(lag.slow, fast, LAG.SLOW, dt);
  return { lag: { fast, slow }, drive: saturateDrive(LAG.GAIN * (fast - slow)) };
}

/**
 * Convert an angle to the CSS rotation that renders it.
 *
 * The two conventions are opposite-handed for something hanging downwards,
 * and it is the kind of wrong that looks deliberate rather than broken.
 *
 * The physics puts the bob at (L·sin θ, L·cos θ) with y downwards, so a
 * positive θ is to the right. CSS rotate(θ) sends a point below the origin
 * to x = −d·sin θ, so a positive rotation takes it to the left: on a clock
 * face, a hand pointing at six moving clockwise goes towards seven and
 * eight, which is the left of the screen.
 *
 * Feeding θ straight to a transform therefore mirrors the whole simulation,
 * and a mirrored trailing tag is an accurately simulated leading tag. It
 * still swings, still settles, still responds to a flick, and is wrong in
 * the one way nothing physical is wrong. Hence one function, one test.
 */
export function cssRotationFor(theta: number): number {
  return (-theta * 180) / Math.PI;
}

export interface PendulumState {
  /** Angle from vertical, radians. */
  theta: number;
  /** Angular velocity, radians per second. */
  omega: number;
}

/**
 * Advance one tag by dt, using semi-implicit (symplectic) Euler.
 *
 * Velocity is updated first and the new velocity moves the position. That
 * ordering is what makes it stable: explicit Euler injects energy every step
 * and an undamped pendulum visibly winds itself up. RK4 would be more
 * accurate, costs four force evaluations, and buys nothing at the accuracy a
 * hanging tag needs.
 *
 * Damping is applied multiplicatively rather than as −c·θ'·dt, which stays
 * stable for any c and dt instead of requiring c·dt < 2.
 *
 * @param drive  horizontal forcing in px/s², from driveFromLag
 * @param length effective pendulum length in px, pivot to centre of mass
 */
export function stepPendulum(
  state: PendulumState,
  dt: number,
  drive: number,
  length: number,
  breeze = 0,
): PendulumState {
  const step = Math.min(dt, PENDULUM.MAX_DT);
  if (step <= 0) return state;

  const L = Math.max(1, length);
  const omega0 = Math.sqrt(PENDULUM.G / L);
  const c = 2 * PENDULUM.ZETA * omega0;

  const alpha =
    -(PENDULUM.G / L) * Math.sin(state.theta) -
    (drive / L) * Math.cos(state.theta) +
    breeze;

  let omega = (state.omega + alpha * step) * Math.exp(-c * step);
  let theta = state.theta + omega * step;

  // Backstop only. saturateDrive keeps the equilibrium inside this, so a
  // tag should reach the limit only by being thrown while already swinging.
  if (theta > PENDULUM.MAX_ANGLE) {
    theta = PENDULUM.MAX_ANGLE;
    // Absorb rather than bounce. A tag that pings off an invisible wall
    // looks like a bug; one that runs out of travel looks like a tag.
    if (omega > 0) omega = 0;
  } else if (theta < -PENDULUM.MAX_ANGLE) {
    theta = -PENDULUM.MAX_ANGLE;
    if (omega < 0) omega = 0;
  }

  return { theta, omega };
}

/**
 * Pointer velocity from a short history rather than the last two events.
 *
 * Taking the last two is the obvious approach and fails three ways: the
 * pointerup event usually repeats the coordinates of the final pointermove,
 * so every drag ends measuring zero; dt can be 0 on a high refresh rate
 * display, giving Infinity; and timestamps are quantised by anti-fingerprint
 * measures.
 *
 * So: a least-squares fit over a 100ms horizon. That horizon is the number
 * Android, Chromium and Motion each arrived at separately, and 40ms of
 * stillness truncates the history so a finger that pauses before lifting
 * releases with no momentum, which is what the user means.
 *
 * The fit is quadratic, and that matters more than it sounds. A straight
 * line through the samples is what this used to do, and it is the strategy
 * Android ships with the comment "Quality: POOR. Frequently underfits the
 * touch data especially when the finger accelerates or changes direction.
 * Often underestimates velocity." A flick is by definition an accelerating
 * drag, so that is the one case it gets wrong: measured against a hand
 * accelerating to 480px/s, the line reports 240. Every throw was leaving at
 * half the speed it was given. A quadratic reports 480 exactly.
 *
 * Android and Chromium both default to this fit for touch. Their own
 * ratings put a cubic at "UNUSABLE. Frequently overfits ... yielding wildly
 * divergent estimates", so two is the ceiling as well as the floor.
 */
const HORIZON_MS = 100;
const STOP_GAP_MS = 40;

export interface Sample {
  x: number;
  t: number;
}

export function trackVelocity(samples: Sample[]): number {
  if (samples.length < 3) return 0;

  const newest = samples[samples.length - 1];
  const usable: Sample[] = [];

  for (let i = samples.length - 1; i >= 0; i--) {
    const sample = samples[i];
    if (newest.t - sample.t > HORIZON_MS) break;
    const next = samples[i + 1];
    if (next && next.t - sample.t > STOP_GAP_MS) break;
    usable.unshift(sample);
  }

  if (usable.length < 3) return 0;

  // A pointerup that repeats the last pointermove's coordinate is the one
  // case the quadratic handles worse than a line, and Android names it:
  // "can be confused ... particularly if the panel has a tendency to
  // generate delayed, duplicate or jittery touch coordinates when the finger
  // is released". Dropping the duplicate removes the problem at the source.
  if (
    usable.length > 3 &&
    usable[usable.length - 1].x === usable[usable.length - 2].x
  ) {
    usable.pop();
  }

  const velocity = fitVelocity(usable) ?? fitSlope(usable) ?? 0;
  // A least-squares fit through a stationary finger lands a hair off zero
  // rather than on it. Sub-pixel-per-second is not movement, and saying so
  // here keeps "stopped means stopped" a property of this function rather
  // than something every caller has to know.
  return Math.abs(velocity) < 1 ? 0 : velocity;
}

/**
 * Velocity at the newest sample from a quadratic least-squares fit.
 *
 * Time is measured in seconds back from the newest sample, so the fit is
 * x = b0 + b1·t + b2·t² with t = 0 at the release and the velocity there is
 * simply b1. Returns null when the samples cannot determine a curve, which
 * happens when they share timestamps or sit in a straight line.
 */
function fitVelocity(samples: Sample[]): number | null {
  const newest = samples[samples.length - 1].t;
  let s0 = 0;
  let s1 = 0;
  let s2 = 0;
  let s3 = 0;
  let s4 = 0;
  let p0 = 0;
  let p1 = 0;
  let p2 = 0;

  for (const { x, t } of samples) {
    const r = (t - newest) / 1000;
    const rr = r * r;
    s0 += 1;
    s1 += r;
    s2 += rr;
    s3 += rr * r;
    s4 += rr * rr;
    p0 += x;
    p1 += x * r;
    p2 += x * rr;
  }

  const det =
    s0 * (s2 * s4 - s3 * s3) -
    s1 * (s1 * s4 - s3 * s2) +
    s2 * (s1 * s3 - s2 * s2);
  if (!Number.isFinite(det) || Math.abs(det) < 1e-12) return null;

  const b1 =
    (s0 * (p1 * s4 - p2 * s3) -
      p0 * (s1 * s4 - s3 * s2) +
      s2 * (s1 * p2 - p1 * s2)) /
    det;
  return Number.isFinite(b1) ? b1 : null;
}

/** Straight-line fallback for samples too degenerate to fit a curve. */
function fitSlope(samples: Sample[]): number | null {
  const n = samples.length;
  let sumT = 0;
  let sumX = 0;
  let sumTT = 0;
  let sumTX = 0;
  for (const { x, t } of samples) {
    const rt = t - samples[0].t;
    sumT += rt;
    sumX += x;
    sumTT += rt * rt;
    sumTX += rt * x;
  }
  const denominator = n * sumTT - sumT * sumT;
  if (Math.abs(denominator) < 1e-6) return null;
  return ((n * sumTX - sumT * sumX) / denominator) * 1000;
}
