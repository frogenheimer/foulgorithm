import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { GeistMono } from "geist/font/mono";
import { Nav } from "@/components/kit/Nav";
import "./tokens.css";
import "./globals.css";

/**
 * Two families. Inter for words, Geist Mono for figures.
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

export const metadata: Metadata = {
  title: "Foulgorithm",
  description:
    "Calibrated probabilities for Premier League fouls, cards and tackles. Every prediction published before kickoff and graded afterwards.",
  icons: { icon: "/icon.svg" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en-GB"
      className={`${inter.variable} ${GeistMono.variable}`}
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
        <Nav>{children}</Nav>
      </body>
    </html>
  );
}
