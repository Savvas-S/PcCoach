import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Inter } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

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
    <html lang="en">
      <body className={inter.className}>
        {children}
        <footer className="border-t border-gray-800 bg-gray-900 text-sm px-4 pt-10 pb-8">
          <div className="max-w-3xl mx-auto space-y-6">
            {/* Brand + nav */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <span className="text-white font-semibold">PcCoach</span>
                <p className="text-gray-500 text-xs mt-0.5">
                  AI-powered PC build recommendations for the European market.
                </p>
              </div>
              <nav className="flex flex-wrap gap-x-6 gap-y-2 text-gray-500">
                <Link href="/about" className="hover:text-white transition-colors">About</Link>
                <Link href="/contact" className="hover:text-white transition-colors">Contact</Link>
                <Link href="/privacy" className="hover:text-white transition-colors">Privacy Policy</Link>
                <Link href="/terms" className="hover:text-white transition-colors">Terms of Service</Link>
              </nav>
            </div>
            {/* Disclosure + copyright */}
            <div className="border-t border-gray-800 pt-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-gray-600 text-xs">
              <p>
                PcCoach participates in affiliate programmes with Amazon, ComputerUniverse, and Caseking.
                We earn a commission on qualifying purchases at no extra cost to you.{" "}
                <Link href="/about#affiliate-disclosure" className="underline hover:text-gray-400 transition-colors">
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
