import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Find a Component — PcCoach",
  description: "Search for a specific PC component. AI recommends the best match with links to all stores.",
};

export default function FindLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
