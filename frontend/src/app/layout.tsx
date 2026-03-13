import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Cormorant_Garamond, Outfit, JetBrains_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const cormorant = Cormorant_Garamond({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  style: ["normal", "italic"],
  variable: "--font-cormorant",
  display: "swap",
});

const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-outfit",
  display: "swap",
});

const jb = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-jb",
  display: "swap",
});

export const metadata: Metadata = {
  title: "PcCoach — AI PC Build Recommender",
  description:
    "Get a complete PC build list, priced and ready to buy. AI picks compatible components and links you directly to Amazon, Caseking, and ComputerUniverse.",
};

export default function RootLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <html lang="en" className={`${cormorant.variable} ${outfit.variable} ${jb.variable}`}>
      <body className="bg-obsidian-bg text-obsidian-text font-body">
        {children}
        <footer className="border-t border-obsidian-border bg-obsidian-surface text-sm px-4 pt-10 pb-8">
          <div className="max-w-3xl mx-auto space-y-6">
            {/* Brand + nav */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <span className="font-display font-light text-lg tracking-wide text-obsidian-text">PcCoach</span>
                <p className="text-obsidian-muted text-xs mt-0.5">
                  AI-powered PC build recommendations for the European market.
                </p>
              </div>
              <nav className="flex flex-wrap gap-x-6 gap-y-2 text-obsidian-muted text-xs uppercase tracking-widest">
                <Link href="/about" className="hover:text-obsidian-text transition-colors">About</Link>
                <Link href="/contact" className="hover:text-obsidian-text transition-colors">Contact</Link>
                <Link href="/privacy" className="hover:text-obsidian-text transition-colors">Privacy</Link>
                <Link href="/terms" className="hover:text-obsidian-text transition-colors">Terms</Link>
              </nav>
            </div>
            {/* Disclosure + copyright */}
            <div className="border-t border-obsidian-border pt-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-obsidian-muted-light text-xs">
              <p>
                As an Amazon Associate I earn from qualifying purchases.{" "}
                PcCoach also participates in other affiliate programmes and may earn a commission on qualifying purchases at no extra cost to you.{" "}
                <Link href="/about#affiliate-disclosure" className="underline hover:text-obsidian-muted transition-colors">
                  Affiliate disclosure
                </Link>
                .
              </p>
              <span className="shrink-0">&copy; 2026 PcCoach</span>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
