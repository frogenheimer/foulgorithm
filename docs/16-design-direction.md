# Design direction

**Status: Proposed, 2026-08-22. Based on research verified the same day.**

## The reframe

The site was described as ugly and dense, and the instinct was to fix it with better visuals and animation. That diagnosis is wrong, or at least incomplete.

**The problem is editorial, not visual.** A page showing 200 numbers with no hierarchy has not decided what it is claiming. Animation applied to an undecided page is lipstick, and worse, motion is the fastest way to make a sober data product look like a tipster site. Betting sites are the most animated surfaces in football: odds flash, numbers tick, greens pulse. Our differentiator is restraint, not motion budget.

Every reference that works well works because **somebody wrote a sentence saying which number matters and why**. Do that first, then animate the reveal of the thing already decided.

## Three changes worth more than the entire visual pass

### 1. "68% chance he fouls" is broken as a sentence

This is the most valuable finding and it is a copy decision, not a design one.

Gigerenzer et al (Risk Analysis, 2005) found the public reads "30% chance of rain" as 30% of the *time* or 30% of the *area*, not 30% of days like this one. Vaughn et al (Meteorological Applications, 2024) confirmed the confusion is about the **reference class**, not about probability, and that comprehension only improved significantly when the forecast was paired with its complement.

So this is wrong:

> 68% chance to commit a foul

And this is right:

> In 68 of 100 matches like this one, he commits at least one foul. In the other 32, he does not.

Natural frequencies with a fixed denominator of 100 (Gigerenzer, BMJ 2011), the reference class stated, and the complement given. Never mix "1 in X" formats with different denominators, because readers anchor on the denominator and 1 in 7 versus 1 in 9 reads backwards to many people.

### 2. Quantile dotplots, not bars or intervals

The strongest evidence-backed finding in the field, and directly usable.

Discretising a distribution into evenly spaced dots lets a reader **count** rather than integrate an area. Fernandes et al (CHI 2018) measured decision quality, not comprehension, and found quantile dotplots produced expected payoffs at **97% of optimal**, five points above control and four points more consistent.

Better still for us: *In Dice We Trust* (CHI 2024) ran ten simulated forecast cycles with 498 participants and found **a plain text summary plus a quantile dotplot sustained the highest trust over time**, well above alternatives. That is precisely our situation: a model that will be visibly wrong some weekends and needs to retain trust anyway.

Use 20 dots on a card. Wilke's *Fundamentals of Data Visualization* warns that too many dots read as a continuum and lose the counting advantage.

### 3. Show outcome spread, not estimate precision

Hofman, Goldstein and Hullman (CHI 2020) found people **overestimate an effect and will pay more for it** when shown confidence intervals rather than prediction intervals. Zhang et al (PNAS 2023) showed even doctors and data scientists confuse the two.

Applied here: show the spread of *individual match outcomes* for a player, not the precision of our estimate of his foul rate. The second flatters the model and is the subtlest credibility-destroying error available to us.

## Confidence tiers, pinned

"Strong / Lean / Thin" was the earlier proposal. Replace it with the UK PHIA Probability Yardstick, which is an operational standard with **deliberate gaps between bands so terms cannot blur**:

| Term | Band |
|---|---|
| Remote chance | ~5% |
| Highly unlikely | 10 to 20% |
| Unlikely | 25 to 35% |
| Realistic possibility | 40 to under 50% |
| Likely | 55 to 75% |
| Highly likely | 80 to 90% |
| Almost certain | ~95% |

If we write "likely" it must always mean 55 to 75%, and the band must be published. Unpinned verbal terms are interpreted wildly differently between readers.

**Drop the decimals.** Our model cannot distinguish 44.87% from 46%. Round to whole numbers, or to 5-point buckets.

## The calibration page

The single highest-credibility, lowest-cost artefact available, and no tipster site has ever built one.

A permanent static page: *of everything we said was 60 to 70% likely, X% happened, across N predictions*. FiveThirtyEight called theirs "Checking Our Work" and it was a large part of why they were trusted. It is a static page fed by data the grading job already produces.

## The regulatory tension, which needs a decision

Research on editorial versus tipster framing turned up a conflict with the direction set in [15-next-phase.md](15-next-phase.md).

| Reads as tipster | Reads as editorial |
|---|---|
| Decimal odds, price floors | Probabilities only |
| "Tips", "picks", "value", "edge" | "Estimate", "chance", "model expects" |
| Red/green verdict colouring | Single-hue sequential ramp |
| No accuracy record | Public calibration page |

The ASA has ruled that content framed as editorial **can still be caught by the CAP Code** where it generates interest in bettable events, and in a 2025 case told Oddschecker to remove posts pairing player images with betting data.

**The price floor idea makes the product more useful and moves it toward the tipster column.** That is a real trade, not a reason to abandon it. Two things follow:

1. Naming specific Premier League players alongside betting guidance engages CAP rule 16.3.12, which restricts content of "strong appeal" to under-18s. Footballers with large young followings are the exact case that rule was written for.
2. The exposure is moderate rather than acute while the site is free with no affiliate links, since Section 16 does not bind a non-operator directly. It sharpens considerably the day money is involved.

Recommendation: **build the price floors, keep the language in the editorial column.** Say "the model expects", never "our tip". Keep the calibration page prominent. Revisit properly before any monetisation. See [13-legal-and-ethics.md](13-legal-and-ethics.md).

## Stack decisions

| Layer | Decision | Reason |
|---|---|---|
| Styling | **Keep CSS Modules. Do not add Tailwind.** | Tailwind's value here is shadcn/ui, which is a copy-paste registry rather than a dependency. Migrating an existing CSS Modules app means running two systems for months |
| Components | **Base UI** `@base-ui/react`, MIT | Stable since Dec 2025, built by the Radix and Floating UI authors, styling-agnostic with a documented CSS Modules path, exposes state as data attributes. Now shadcn's own default |
| Charts | **Hand-rolled SVG with `d3-scale` and `d3-shape`**, ISC | We need four chart types. That is 200 lines of JSX, not a dependency. Static export means rendering them at build time as Server Components: zero client JavaScript, free dark mode, full control of the accessibility layer |
| Animation | **CSS first**: `@starting-style` (90.7%), `@property` (94.2%), `transition-behavior: allow-discrete` (90.7%), `animation-timeline: view()` (85.4%) behind `@supports` | Entrance animation, popover transitions and animated custom properties no longer need JavaScript. Zero bytes |
| Animation escape hatch | **Motion 13** via `LazyMotion` + `m` from `motion/react-m` | The full `motion` component cannot tree-shake below 34kb. `LazyMotion` gets initial render under 4.6kb. 34kb to fade cards in is indefensible when `@starting-style` is free |
| Disclosure | Native `<details name>` + `::details-content` + `grid-template-rows: 0fr → 1fr` | No library, free keyboard handling, and Chrome's find-in-page opens closed details |
| Fonts | **Newsreader or Instrument Serif** headlines, **Inter** for UI and numerals, self-hosted | Both OFL 1.1, both variable. A serif headline signals editorial immediately, which is exactly the positioning we want |
| Type and space | **Utopia** fluid `clamp()` scales | Kills breakpoint-specific typography, which matters on pages mixing prose, tables and charts |
| Layout | Named-line content grid, container queries (94.1%), subgrid (92.4%) | Handles prose at `60ch`, breakout tables and full-bleed charts in one grid with no wrapper divs |

Target new client-side JavaScript: **0 to 20kb**.

**Rejected:** GSAP (bespoke non-OSI licence, four months without a repo push, and we need none of its strengths), Tremor (npm stalled since Jan 2025), Park UI (dormant), Magic UI and Aceternity (marketing-page effects, precisely the tackiness to avoid), uPlot and ECharts (built for high-cardinality time series, we have 20 rows), View Transitions for page transitions (still experimental in Next).

## Animation rules, revised

**Never animate a number.** A probability counting up from 0 to 68 is unreadable for the duration and reads as a slot machine. **Animate the bar, print the number.** If a number must transition, `tabular-nums` is mandatory or the layout shifts every frame.

**Any motion that encodes uncertainty must be captioned in words on the same screen.** The New York Times election needle is the best-documented failure here: its jitter was genuinely well designed, bounded by the 25th to 75th percentile and narrowing as certainty grew, but nothing on screen explained that, so readers read motion as anxiety. It was removed.

**Never let a draw-on animation delay reading a value.** Draw the line, render the number at full opacity immediately.

**Opt in to motion, do not opt out.** Wrap animation in `@media (prefers-reduced-motion: no-preference)` rather than disabling it afterwards.

## The information hierarchy

Adapted from the UK Government Analysis Function guidance on communicating uncertainty, which specifies exactly this layering:

**Two levels, not four.** An earlier draft of this doc proposed four. Nielsen is
explicit that "designs that go beyond 2 disclosure levels typically have low
usability because users often get lost when moving between the levels", so the
four collapse into two:

- **Level 1, visible.** The answer sentence, a 20-dot quantile dotplot, a
  whole-number percentage and a pinned band word, then the ranked table. Three
  encodings of one fact, which is the redundancy the trust research rewards.
- **Level 2, on demand.** Method, sample size, run date, calibration, full line
  grid. In a `<details>`, always present, never in the way.

**Never a full-screen hero with one sentence and nothing else.** NN/g found six
of eight users did not realise they could scroll on such a page. Always leave the
top edge of the next block visible, so the page cannot manufacture a false floor.

**The current site is Level 2 content shown as Level 1.** That is the problem,
stated precisely.

### Frequencies beat probabilities, and it is not close

Westwood, Messing and Lelkes (*Journal of Politics*, 2020) found probabilistic
forecasts **increase certainty and confuse people**, and that win probabilities
convey substantially more confidence than an equivalent rate-based statement of
the same model output.

Applied: "65% chance of a foul" is read as near-certainty by a meaningful share
of readers. "In 13 of his last 20 matches" is not. Lead with the frequency.

Budescu et al (*Nature Climate Change*, 2014, 25 samples across 24 countries)
found pairing a word with a number lifted correct interpretation from 27% to
40%. Note what that means: **even with both, most readers still misplace the
range.** A band word alone is not close to sufficient.

**Never use "1 in X".** Galesic and Garcia-Retamero asked which is the biggest
risk out of 1 in 100, 1 in 1,000 and 1 in 10. Only about three quarters of
respondents got it right. A quarter of the public cannot order those fractions.

### Two corrections to earlier decisions

**`<details>` is findable now.** The old "collapsed content is invisible to
Ctrl+F and bad for SEO" objection is out of date for the native element: all
three engines find and reveal it as of early 2026, and Google's mobile-first
guidance now actively recommends moving content into accordions rather than
removing it. A hand-rolled `display: none` accordion is still invisible, which
makes it a self-inflicted wound rather than a platform limit.

**Instrument Serif has no tabular figures at all.** Neither does Fraunces. Fine
for headlines, disqualifying for anything numeric. Use **Newsreader**, which is
tabular by default, or keep the serif strictly to headlines.

**Inter is the right numeral font** because its tabular and slashed-zero variants
compose. Note that Geist implements slashed zero as `ss09` rather than `zero`, so
the standard CSS silently does nothing there, and IBM Plex is *always* tabular
with no proportional option, which makes prose read gappy.

Use `font-variant-numeric`, not `font-feature-settings`: the former inherits and
composes, the latter replaces the whole feature set on every declaration.

### Accordion affordances, from the one study with numbers

136 participants, first-click tasks: **a caret beats no icon and beats a nonsense
icon**, both significant. A plus sign or a right-facing arrow is no better than
nothing. 29% of taps land on the label even when a caret is present, so **label
and icon must share one hit area**, never a split button.

Labels must front-load meaning. "How we worked this out" and "His last 10
matches", never "Details", "More info" or "Advanced".

## Do these before touching any CSS

1. **Write the sentence.** For every fixture, one plain-English claim with the reference class explicit and the complement stated. If it cannot be written, the page has no answer to lead with.
2. **Drop the decimals** and adopt the pinned bands.
3. **Build the calibration page.** Highest credibility per unit of effort on this entire list.
