import type { Metadata } from "next";
import { Rail } from "@/components/ui/Rail";
import "./globals.css";

export const metadata: Metadata = {
  title: "Foulgorithm",
  description:
    "Calibrated probabilities for Premier League fouls, cards and tackles. Every prediction published before kickoff and graded afterwards.",
  icons: { icon: "/icon.svg" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en-GB" suppressHydrationWarning>
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
        <Rail>{children}</Rail>
      </body>
    </html>
  );
}
