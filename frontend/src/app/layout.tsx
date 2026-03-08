import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "PcCoach",
  description: "AI-powered PC building assistant",
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
        <footer className="text-center text-gray-500 text-xs py-6 px-4">
          As an Amazon Associate I earn from qualifying purchases.
        </footer>
      </body>
    </html>
  );
}
