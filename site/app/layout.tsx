import type { Metadata } from "next";
import { Rail } from "@/components/ui/Rail";
import "./globals.css";

export const metadata: Metadata = {
  title: "Foulgorithm",
  description:
    "Calibrated probabilities for Premier League fouls, cards and tackles. Every prediction published before kickoff and graded afterwards.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en-GB">
      <body>
        <Rail>{children}</Rail>
      </body>
    </html>
  );
}
