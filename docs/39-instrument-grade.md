# Instrument-grade: the visual redesign

**Status: Decided 2026-08-25, Oliver's sign-off on the four foundations.**
The site's information design was rebuilt under [docs/38](38-the-contract.md);
this decides how it should LOOK. The reference points are motion.dev (one hot
accent on near-black, disciplined type, spring interactions, grouped nav) and
a modular dashboard aesthetic (self-contained rounded modules, one gradient
hero per page, stat tiles and meters wherever numbers currently sit naked).
The honesty rules survive in full: losses as visible as wins, no probability
without its uncertainty, colour never alone, tokens only.

---

## 🎯 The four decided foundations

1. **Dark-first.** Every module is designed on the dark theme; light becomes
   the derived variant. This flips the current order.
2. **A new accent.** The brand gets its own accent (electric territory,
   validated before it enters tokens.css); green retires to purely semantic
   good/won duty. One accent stays the law.
3. **The motion amendment.** Interactions get spring physics; page entry gets
   ONE subtle module stagger (roughly 60ms steps, opacity plus a 4px rise,
   none of it under prefers-reduced-motion). Two bans stay absolute:
   **numbers never count up, charts never draw themselves.** Life in the
   chrome, never in the data.
4. **Club badges, not crests.** Generic badges in each club's official kit
   colours. Crest artwork is trademarked and copyrighted, and a betting-
   adjacent site wearing twenty official crests invites exactly the letter
   the Premier League is known for sending; kit colour pairs are facts. The
   badge slot is crest-ready if a licence ever exists.

## 🛡️ The badge: the temper ring

A circular two-tone badge, club primary with a diagonal sash in the
secondary, a three-letter code in the middle, and the interesting element:
a thin outer arc, the **temper ring**, filled by the club's fouls per match
against the league. Our badges are instruments: Chelsea's crest literally
wears how much fight they bring. The ring pairs with words wherever it
appears (a tooltip or caption carrying the number and rank), colour never
alone. Kit colours live in `site/lib/clubs.json` as data; unknown clubs fall
back to a neutral badge with a derived code, so a promoted visitor never
crashes a page.

## 🧱 The module system (build order 2)

One `Module` primitive: header (title, context chip, one action), body,
footer. One gradient hero module per page, maximum. Inside modules, a small
vocabulary: stat tile (display number, delta chip, sparkline), meter (label,
bar, value/target), slip (built), chips (status, v2, hot, delta), club
badge, DataTable v2 (borderless, hover raise).

**Amended 2026-08-25, Oliver's call: SHARP.** Radius goes to zero, boxes are
boxes, contrast carries the depth, and the personality lives in snap-eased
hover states (--ease-snap) rather than rounded softness. Only the pill
survives, because a swatch is a circle, not a box. The accent is electric
cyan (#0b7e90 light / #21c7dc dark, both clearing AA), and green retires to
purely semantic good/won duty. Space Grotesk joins as the display face for
titles and hero numbers.

## 📊 The chart vocabulary (build order 4-5)

All through the palette validator, per the brandbook's colour rules:

- **Bump chart**: league positions over rounds, eleven character-coloured
  lines. The product's signature image once three rounds exist.
- **Sparklines**: form under every headline number.
- **Mirrored bars**: the head-to-head sheet's club comparison, two bars
  meeting in the middle per metric, rank chips at the ends.
- **Stepped funnel**: claims published → settled → graded → won, on the
  track record page.
- **PMF area charts**: the explorer's distributions, soft filled curves.
- **Lineage timeline**: magicIan's genome per generation, small multiples.
- **Dial signatures v2**: the character dials on raised wells.

## ✅ Page map

| Page | Modules, top to bottom |
|---|---|
| Home | Hero: next kickoff + expected fouls. Calendar strip. Fixture cards with badges, crossover, sparkline. Table snapshot. |
| Fixture, upcoming | Badge pair header. Pitch. Head-to-head as mirrored bars + referee strip. Players top-10. Bets compact-then-expand. Ladder. |
| Fixture, played | Hero: score and fouls in display type. Bets marked. Ladder marked. |
| The league | Hero: the table with movement and form dots. Bump chart. Bets per game, compact-then-expand. Character gallery. |
| Character detail | Colour hero. Dial signature. Record sparkline. Ian: lineage timeline. |
| Track record | Hero: calibration headline. Funnel. Reliability v2. Per-model meters. |
| Teams, History, Methodology | Same module system, badges throughout. |

## 🚦 Delivery order

1. This spec; club badges built and seeded (teams table, fixture headers).
2. Tokens v2 (dark-first surfaces, radius, elevation, display type, new
   accent through the validator) + brandbook v2 rewrite + audit update.
3. Module primitive + nav restyle; pages migrate one per commit.
4. Chart vocabulary, page by page.
5. Bump chart and lineage timeline once round data exists.
6. Density: compact-then-expand bets everywhere.

Each step behind make check, the mobile script at 390 and 320, and the
palette validator for any colour that encodes data.
