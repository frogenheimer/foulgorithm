import type { Metadata, Viewport } from "next";
import { Inter, Space_Grotesk } from "next/font/google";
import { GeistMono } from "geist/font/mono";
import { Nav } from "@/components/kit/Nav";
import "./tokens.css";
import "./globals.css";

/**
 * Three families, each load-bearing. Inter for words, Geist Mono for
 * figures, Space Grotesk for display: page titles and hero numbers, the
 * instrument-panel voice of the redesign (docs/39). All self-hosted through
 * next/font.
 *
 * `cv05` gives Inter a single-storey `a` and `tnum` turns on tabular figures
 * globally, so no component has to remember to align a column of numbers.
 *
 * Both are self-hosted through next/font: no third-party request, no layout
 * shift, and the site keeps working if Google Fonts is unreachable.
 */
const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
  axes: ["opsz"],
});

const display = Space_Grotesk({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-space",
  weight: ["500", "600"],
});

export const metadata: Metadata = {
  title: "Foulgorithm",
  description:
    "Calibrated probabilities for Premier League fouls, cards and tackles. Every prediction published before kickoff and graded afterwards.",
  icons: { icon: "/icon.svg" },
};

/* The rail's colour, so the browser chrome on a phone matches the site.
   Literals, because a meta tag cannot read tokens.css. */
export const viewport: Viewport = {
  themeColor: [
    // audit-ignore B10: theme-color meta needs literals; these are --rail from tokens.css
    { media: "(prefers-color-scheme: light)", color: "#16181a" },
    { media: "(prefers-color-scheme: dark)", color: "#0a0b0c" },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en-GB"
      className={`${inter.variable} ${GeistMono.variable} ${display.variable}`}
      suppressHydrationWarning
    >
      <head>
        {/* Applies the stored theme before first paint. Doing this in a
            component would flash the wrong theme for a frame on every load. */}
        <script
          dangerouslySetInnerHTML={{
            __html: `try{var t=localStorage.getItem("theme");if(t==="light"||t==="dark")document.documentElement.setAttribute("data-theme",t)}catch(e){}`,
          }}
        />
      </head>
      <body>
        {/* First thing focus meets. Invisible until it is. */}
        <a className="skip" href="#main">
          Skip to content
        </a>
        <Nav>{children}</Nav>
      </body>
    </html>
  );
}
