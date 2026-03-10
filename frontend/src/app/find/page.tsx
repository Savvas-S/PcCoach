"use client";

import { useState } from "react";
import Link from "next/link";
import { searchComponent } from "@/lib/api";
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
];

const SOURCE_LABELS: Record<string, string> = {
  amazon: "Amazon.de",
  computeruniverse: "ComputerUniverse",
  caseking: "Caseking",
};

const SOURCE_COLORS: Record<string, string> = {
  amazon: "bg-orange-600 hover:bg-orange-500",
  computeruniverse: "bg-blue-700 hover:bg-blue-600",
  caseking: "bg-red-700 hover:bg-red-600",
};

export default function FindPage() {
  const [category, setCategory] = useState<ComponentCategory | null>(null);
  const [description, setDescription] = useState("");
  const [budget, setBudget] = useState("");
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
      const res = await searchComponent(
        {
          category,
          description: description.trim(),
          budget_eur: budget ? parseFloat(budget) : undefined,
        },
        controller.signal
      );
      setResult(res);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Something went wrong. Please try again.";
      setError(msg);
    } finally {
      setLoading(false);
      clearTimeout(timeout);
    }
  };

  return (
    <main className="min-h-screen bg-gray-900 text-white py-12 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="mb-10">
          <Link href="/" className="text-gray-400 hover:text-white text-sm">
            &larr; Back
          </Link>
          <h1 className="text-3xl font-bold mt-4">Find a Component</h1>
          <p className="text-gray-400 mt-1">
            Tell us what you&apos;re looking for and we&apos;ll recommend the best match with store links.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Category */}
          <section>
            <h2 className="text-lg font-semibold mb-4">What type of component?</h2>
            <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
              {CATEGORIES.map((c) => (
                <button
                  key={c.value}
                  type="button"
                  onClick={() => setCategory(c.value)}
                  className={`p-3 rounded-xl border text-sm font-medium transition-all flex flex-col items-center gap-1 ${
                    category === c.value
                      ? "border-blue-500 bg-blue-500/10 text-blue-400"
                      : "border-gray-700 bg-gray-800 hover:border-gray-500 text-white"
                  }`}
                >
                  <span className="text-xl">{c.icon}</span>
                  {c.label}
                </button>
              ))}
            </div>
          </section>

          {/* Description */}
          <section>
            <label className="text-lg font-semibold mb-4 block">
              Describe what you need
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={
                category === "cpu"
                  ? "e.g. best gaming CPU under €300, prefer AMD"
                  : category === "gpu"
                  ? "e.g. RTX 4070 or equivalent for 1440p gaming"
                  : "e.g. describe the component, use case, or specific model"
              }
              maxLength={300}
              rows={3}
              className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 resize-none"
            />
            <p className="text-gray-600 text-xs mt-1 text-right">{description.length}/300</p>
          </section>

          {/* Budget (optional) */}
          <section>
            <label className="text-lg font-semibold mb-4 block">
              Max budget{" "}
              <span className="text-gray-500 font-normal text-sm">(optional)</span>
            </label>
            <div className="relative w-40">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">€</span>
              <input
                type="number"
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
                placeholder="e.g. 300"
                min={1}
                className="w-full bg-gray-800 border border-gray-700 rounded-xl pl-8 pr-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
              />
            </div>
          </section>

          {error && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl p-4 text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={!category || !description.trim() || loading}
            className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 disabled:cursor-not-allowed text-white font-semibold py-4 rounded-xl text-lg transition-colors"
          >
            {loading ? "Finding best match…" : "Find Component →"}
          </button>
        </form>

        {/* Result */}
        {result && (
          <div className="mt-10 bg-gray-800 border border-gray-700 rounded-xl p-6">
            <div className="flex items-start justify-between gap-4 mb-4">
              <div>
                <span className="text-xs font-medium text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded-full">
                  {CATEGORIES.find((c) => c.value === result.category)?.label ?? result.category}
                </span>
                <h2 className="text-xl font-bold text-white mt-2">{result.name}</h2>
                <p className="text-gray-400 text-sm">{result.brand}</p>
              </div>
              <div className="text-right shrink-0">
                <div className="text-2xl font-bold text-white">
                  ~€{result.estimated_price_eur.toFixed(0)}
                </div>
                <div className="text-xs text-gray-500 mt-1">estimated</div>
              </div>
            </div>

            {Object.keys(result.specs).length > 0 && (
              <div className="flex flex-wrap gap-2 mb-4">
                {Object.entries(result.specs).map(([k, v]) => (
                  <span
                    key={k}
                    className="text-xs text-gray-400 bg-gray-700/60 px-2 py-1 rounded-lg"
                  >
                    {k}: {v}
                  </span>
                ))}
              </div>
            )}

            <p className="text-gray-300 text-sm leading-relaxed mb-6">{result.reason}</p>

            <div>
              <p className="text-xs text-gray-500 mb-3 uppercase tracking-wide">Search on stores</p>
              <div className="flex flex-wrap gap-2">
                {result.store_links.map((link) => (
                  <a
                    key={link.store}
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={`${SOURCE_COLORS[link.store] ?? "bg-gray-700 hover:bg-gray-600"} text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors`}
                  >
                    {SOURCE_LABELS[link.store] ?? link.store} →
                  </a>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
