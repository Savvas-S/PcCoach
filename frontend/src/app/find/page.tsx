"use client";

import { useState } from "react";
import Link from "next/link";
import { searchComponent, SOURCE_LABELS } from "@/lib/api";
import { safeAffiliateUrl } from "@/lib/url";
import { priceRange } from "@/lib/price";
import { ErrorModal } from "@/components/ErrorModal";
import type { ComponentCategory, ComponentSearchResult } from "@/lib/api";

const CATEGORIES: { value: ComponentCategory; label: string; icon: string }[] = [
  { value: "cpu", label: "CPU", icon: "🔲" },
  { value: "gpu", label: "GPU", icon: "🎮" },
  { value: "motherboard", label: "Motherboard", icon: "🔌" },
  { value: "ram", label: "RAM", icon: "💾" },
  { value: "storage", label: "Storage", icon: "💿" },
  { value: "psu", label: "PSU", icon: "⚡" },
  { value: "case", label: "Case", icon: "🖥️" },
  { value: "cooling", label: "Cooling", icon: "❄️" },
  { value: "monitor", label: "Monitor", icon: "🖵" },
  { value: "keyboard", label: "Keyboard", icon: "⌨️" },
  { value: "mouse", label: "Mouse", icon: "🖱️" },
  { value: "toolkit", label: "Toolkit", icon: "🔧" },
];

const CATEGORY_PLACEHOLDERS: Record<ComponentCategory, string> = {
  cpu: "e.g. best gaming CPU under €300, prefer AMD",
  gpu: "e.g. RTX 4070 or equivalent for 1440p gaming",
  motherboard: "e.g. ATX board for AM5, good VRM for overclocking",
  ram: "e.g. 32 GB DDR5 kit, low latency",
  storage: "e.g. 2 TB NVMe SSD, PCIe 4.0",
  psu: "e.g. 850W modular, 80+ Gold",
  case: "e.g. mid-tower ATX with good airflow and USB-C front panel",
  cooling: "e.g. 240mm AIO for Ryzen 7 CPU, quiet fans",
  monitor: "e.g. 27\" 1440p 165Hz IPS for gaming",
  keyboard: "e.g. compact TKL mechanical, tactile switches",
  mouse: "e.g. lightweight wireless gaming mouse under €80",
  toolkit: "e.g. precision screwdriver set for PC building",
};

const SPEC_KEY_OVERRIDES: Record<string, string> = {
  tdp: "TDP",
  rpm: "RPM",
  vram: "VRAM",
  pcie: "PCIe",
  ddr: "DDR",
};

function formatSpecKey(key: string): string {
  const lower = key.toLowerCase();
  if (SPEC_KEY_OVERRIDES[lower]) return SPEC_KEY_OVERRIDES[lower];
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

const selectedCls = "border-obsidian bg-obsidian/10 text-obsidian";
const unselectedCls =
  "border-obsidian-border bg-obsidian-surface hover:border-obsidian-bright text-obsidian-text";

export default function FindPage() {
  const [category, setCategory] = useState<ComponentCategory | null>(null);
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ComponentSearchResult | null>(null);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!category || !description.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 60_000);
    try {
      const res = await searchComponent({ category, description: description.trim() }, controller.signal);
      setResult(res);
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") {
        setError("Request timed out. Please try again.");
      } else {
        setError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
      }
    } finally {
      setLoading(false);
      clearTimeout(timeout);
    }
  };

  return (
    <main className="min-h-screen bg-obsidian-bg/50 py-12 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="mb-12">
          <Link href="/" className="text-obsidian-muted hover:text-obsidian-text text-xs uppercase tracking-widest transition-colors">
            &larr; Back
          </Link>
          <h1 className="font-display font-light text-5xl text-obsidian-text mt-6 mb-2">Find a Component</h1>
          <p className="text-obsidian-muted text-sm">
            Tell us what you&apos;re looking for and we&apos;ll recommend the best match with store links.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-1">
          {/* Category */}
          <section className="bg-obsidian-surface/50 border border-obsidian-border p-8">
            <h2 className="font-body font-semibold text-obsidian-text mb-6">What type of component?</h2>
            <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
              {CATEGORIES.map((c) => (
                <button
                  key={c.value}
                  type="button"
                  aria-label={c.label}
                  aria-pressed={category === c.value}
                  onClick={() => setCategory(c.value)}
                  className={`p-3 border text-sm font-body font-medium transition-all flex flex-col items-center gap-1.5 ${
                    category === c.value ? selectedCls : unselectedCls
                  }`}
                >
                  <span aria-hidden="true" className="text-xl">{c.icon}</span>
                  {c.label}
                </button>
              ))}
            </div>
          </section>

          {/* Description */}
          <section className="bg-obsidian-surface/50 border border-obsidian-border p-8">
            <label className="font-body font-semibold text-obsidian-text mb-5 block">
              Describe what you need
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={
                category
                  ? CATEGORY_PLACEHOLDERS[category]
                  : "e.g. describe the component, use case, or specific model"
              }
              maxLength={300}
              rows={3}
              className="w-full bg-obsidian-raised border border-obsidian-border px-4 py-3 text-obsidian-text placeholder-obsidian-muted-light focus:outline-none focus:border-obsidian resize-none transition-all text-sm font-body"
            />
            <p className="text-obsidian-muted-light text-xs mt-1 text-right font-mono">{description.length}/300</p>
          </section>

          <div className="pt-2">
            <button
              type="submit"
              disabled={!category || !description.trim() || loading}
              className={`w-full py-4 text-base font-body font-semibold transition-all ${
                !category || !description.trim() || loading
                  ? "bg-obsidian-surface/50 border border-obsidian-border text-obsidian-muted cursor-not-allowed"
                  : "btn-shimmer bg-obsidian text-obsidian-bg hover:brightness-110 hover:shadow-[0_0_25px_rgba(217,119,6,0.25)]"
              }`}
            >
              {loading ? "Finding best match…" : "Find Component →"}
            </button>
          </div>
        </form>

        {/* Result */}
        {result && (
          <div className="mt-8 bg-obsidian-surface/50 border border-obsidian-border p-6">
            <div className="flex items-start justify-between gap-4 mb-5">
              <div>
                <span className="text-xs font-body text-obsidian border border-obsidian/30 px-2 py-0.5 uppercase tracking-wider">
                  {CATEGORIES.find((c) => c.value === result.category)?.label ?? result.category}
                </span>
                <h2 className="font-display font-normal text-2xl text-obsidian-text mt-3">{result.name}</h2>
                <p className="text-obsidian-muted text-sm mt-0.5">{result.brand}</p>
              </div>
              <div className="text-right shrink-0">
                <div className="font-mono text-sm text-obsidian-muted">
                  Est: {priceRange(result.estimated_price_eur)}
                </div>
              </div>
            </div>

            {Object.keys(result.specs).length > 0 && (
              <div className="flex flex-wrap gap-2 mb-5">
                {Object.entries(result.specs).map(([k, v]) => (
                  <span
                    key={k}
                    className="font-mono text-xs text-obsidian-muted border border-obsidian-border px-2 py-1"
                  >
                    {formatSpecKey(k)}: {v}
                  </span>
                ))}
              </div>
            )}

            <p className="text-obsidian-text text-sm leading-relaxed mb-6">{result.reason}</p>

            {result.affiliate_url && result.affiliate_source && (
              <div>
                <div className="flex flex-wrap gap-2">
                  {(() => {
                    const safeUrl = safeAffiliateUrl(result.affiliate_url);
                    if (!safeUrl) return null;
                    return (
                      <a
                        href={safeUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-shimmer inline-block bg-obsidian text-obsidian-bg font-body font-semibold text-xs px-4 py-2.5 hover:brightness-110 transition-all whitespace-nowrap uppercase tracking-wide"
                      >
                        Check Current Price on{" "}
                        {result.affiliate_source
                          ? SOURCE_LABELS[result.affiliate_source]
                          : "Amazon"} &rarr;
                      </a>
                    );
                  })()}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {error && <ErrorModal message={error} onDismiss={() => setError(null)} />}
    </main>
  );
}
