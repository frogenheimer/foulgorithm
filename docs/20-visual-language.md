# Visual language

**Status: Proposed, 2026-08-22.**

Drawn from two references: the Slate palette, and `nerochain.io` for motion.

⚠️ **I could not render nerochain.io.** It paints nothing without scroll, even
given 20 seconds of virtual time, so everything below about its motion is
inference from the genre rather than observation. Worth a second look with a
real browser before we commit to any of it.

## The palette, and the line it must not cross

Slate: `#4DBE55` `#79ED91` `#71776D` `#698696` `#BEBEBE`

**Validated, and it fails as a data palette.** Run against the checker:

- **Chroma floor FAIL.** `#71776D`, `#698696` and `#BEBEBE` all read as grey.
- **Normal-vision floor FAIL.** `#698696` against `#71776D` is ΔE 6.3, below the
  floor of 15. Those two are hard to tell apart *with full colour vision*,
  before colour blindness enters it.
- **Contrast WARN.** `#4DBE55` at 2.38:1, `#79ED91` at 1.46:1 and `#BEBEBE` at
  1.86:1 all sit under 3:1 on white.

**This is not a reason to reject the palette. It is a reason to scope it.**

| Use | Verdict |
|---|---|
| Brand mark, active nav, primary button, focus ring, highlights | **Yes.** Chrome does not encode anything, and a low-contrast green behind dark text is fine |
| Chart series, heat scales, anything where colour carries meaning | **No.** Use the validated blue sequential ramp |

Green is also the single worst hue to lean on for encoding, because red-green
deficiency affects roughly 8% of men. A green-dominant *interface* is fine. A
green-dominant *chart* is not.

**So: green is the brand, blue is the data.** That separation is also good
practice on its own terms, since it means an accent can never be mistaken for a
value.

## Ideas taken

**1. One saturated accent on a near-neutral field.** Both references do this:
almost everything is grey or near-black, one colour carries every action. We
already had this rule and were not using it hard enough.

**2. Dark as the primary mode**, not an afterthought. The genre assumes dark and
tunes light second. Our tokens already support both; the defaults should favour
dark.

**3. Technical typography.** Monospace display, tight tracking, uppercase
micro-labels. Already adopted for headings.

**4. Scroll-reveal, gated.** Content fading and rising as it enters the
viewport. Cheap now that `animation-timeline: view()` is at 85% support, so it
costs no JavaScript. **Gated behind `@supports` and
`prefers-reduced-motion`**, and never applied to a number a reader is trying to
read.

**5. A faint structural background.** A dot or grid field at very low opacity
gives depth without imagery, which matters when we have no licence for any
photography.

**6. Accent glow, used once per screen.** A soft halo on the single most
important element. Effective precisely because it is rationed.

**7. Elevated cards on a darker plane.** Surfaces slightly lighter than the
page, hairline borders, no shadows.

## Ideas rejected

**Animated counters.** Ubiquitous in this genre and actively harmful here: a
number is unreadable while it counts, and ours are probabilities.

**Gradient text on data.** Fine on a hero word, never on a value.

**Scroll-jacking and pinned sections.** They suit a narrative marketing page.
This is a tool people arrive at with a question.

**Full-bleed alternating sections.** Same reason. One shell, dense content.

## The constraint that outranks all of it

Every number keeps its uncertainty, its sample size and its band word. A
prettier surface must not quietly turn an estimate into a promise, and if a
visual idea makes a probability feel more certain than it is, that idea loses.
