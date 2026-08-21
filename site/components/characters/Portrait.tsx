/**
 * Abstract portraits, one per character.
 *
 * A shared circular frame so they read as a set, with internal geometry that
 * expresses the temperament. Deliberately geometric rather than illustrative:
 * this is a page about probability, and cartoon faces would undercut it.
 *
 * Colours come from the validated categorical palette. Three of the five sit
 * below 3:1 on the light surface, so a name label always accompanies a portrait
 * and colour never carries identity alone. See docs/ui-styleguide.md.
 */

export const CHARACTER_COLOUR: Record<string, string> = {
  alan: "var(--char-alan)",
  lily: "var(--char-lily)",
  valentina: "var(--char-valentina)",
  tayler: "var(--char-tayler)",
  bdog: "var(--char-bdog)",
};

function Frame({ colour, children }: { colour: string; children: React.ReactNode }) {
  return (
    <>
      <circle cx="60" cy="60" r="54" fill="none" stroke={colour} strokeWidth="1.5" opacity="0.35" />
      {children}
    </>
  );
}

/** Anger: everything sharp, everything pointing out. Nothing curved. */
function Alan({ c }: { c: string }) {
  const spikes = Array.from({ length: 12 }, (_, i) => {
    const a = (i / 12) * Math.PI * 2 - Math.PI / 2;
    const inner = 20;
    const outer = i % 2 === 0 ? 46 : 32;
    return `${60 + Math.cos(a) * inner},${60 + Math.sin(a) * inner} ${60 + Math.cos(a + 0.13) * outer},${60 + Math.sin(a + 0.13) * outer}`;
  }).join(" ");
  return (
    <Frame colour={c}>
      <polygon points={spikes} fill={c} opacity="0.9" />
      <circle cx="60" cy="60" r="9" fill="var(--surface-1)" />
    </Frame>
  );
}

/** Lust: overlapping curves, drawn toward one another, nothing straight. */
function Lily({ c }: { c: string }) {
  return (
    <Frame colour={c}>
      {[0, 60, 120].map((rot) => (
        <ellipse
          key={rot}
          cx="60"
          cy="60"
          rx="40"
          ry="17"
          fill={c}
          opacity="0.34"
          transform={`rotate(${rot} 60 60)`}
        />
      ))}
      <circle cx="60" cy="60" r="8" fill={c} />
    </Frame>
  );
}

/** Violence: two blades crossing. The only mark that breaks its own frame. */
function Valentina({ c }: { c: string }) {
  return (
    <Frame colour={c}>
      <path d="M22 22 L98 98" stroke={c} strokeWidth="9" strokeLinecap="butt" />
      <path d="M98 22 L22 98" stroke={c} strokeWidth="9" strokeLinecap="butt" />
      <path d="M14 60 L106 60" stroke={c} strokeWidth="2.5" opacity="0.55" />
      <circle cx="60" cy="60" r="11" fill="var(--surface-1)" stroke={c} strokeWidth="2.5" />
    </Frame>
  );
}

/** Terror: contracted to the middle, rings closing in, a lot of empty space. */
function Tayler({ c }: { c: string }) {
  return (
    <Frame colour={c}>
      {[44, 34, 25, 17].map((r, i) => (
        <circle
          key={r}
          cx="60"
          cy="60"
          r={r}
          fill="none"
          stroke={c}
          strokeWidth="1.6"
          opacity={0.18 + i * 0.16}
          strokeDasharray={i < 3 ? "3 5" : undefined}
        />
      ))}
      <circle cx="60" cy="60" r="6" fill={c} />
    </Frame>
  );
}

/** Bravery: one shape stepping forward while the rest hold the line. */
function Bdog({ c }: { c: string }) {
  return (
    <Frame colour={c}>
      {[0, 1, 2, 3].map((i) => (
        <rect key={i} x={22 + i * 20} y={64} width="11" height="26" rx="2.5" fill={c} opacity="0.28" />
      ))}
      <path d="M60 18 L84 56 L60 46 L36 56 Z" fill={c} />
      <circle cx="60" cy="60" r="4" fill="var(--surface-1)" />
    </Frame>
  );
}

const MARKS: Record<string, (p: { c: string }) => React.JSX.Element> = {
  alan: Alan,
  lily: Lily,
  valentina: Valentina,
  tayler: Tayler,
  bdog: Bdog,
};

export default function Portrait({
  id,
  size = 120,
  label,
}: {
  id: string;
  size?: number;
  label: string;
}) {
  const Mark = MARKS[id];
  const colour = CHARACTER_COLOUR[id] ?? "var(--series-1)";
  if (!Mark) return null;
  return (
    <svg
      viewBox="0 0 120 120"
      width={size}
      height={size}
      style={{ width: size, height: size, flexShrink: 0 }}
      role="img"
      aria-label={`${label} portrait`}
    >
      <Mark c={colour} />
    </svg>
  );
}
