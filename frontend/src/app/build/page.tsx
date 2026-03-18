"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { submitBuild } from "@/lib/api";
import { ErrorModal } from "@/components/ErrorModal";
import type {
  UserGoal,
  BudgetRange,
  FormFactor,
  CPUBrand,
  GPUBrand,
  CoolingPreference,
  ComponentCategory,
} from "@/lib/api";
// Edit shared/budget_goals.json and run `make sync-config` to update all services.
import budgetGoalsData from "@/lib/budget_goals.json";

const GOALS: { value: UserGoal; label: string; desc: string; icon: string }[] =
  [
    { value: "high_end_gaming", label: "High-End Gaming", desc: "4K, max settings, 144fps+", icon: "🎮" },
    { value: "mid_range_gaming", label: "Mid-Range Gaming", desc: "1080p/1440p, high settings", icon: "🕹️" },
    { value: "low_end_gaming", label: "Budget Gaming", desc: "1080p, medium settings", icon: "👾" },
    { value: "light_work", label: "Everyday Use", desc: "Office, web, video calls", icon: "💼" },
    { value: "heavy_work", label: "Power User", desc: "Video editing, rendering, VMs", icon: "⚙️" },
    { value: "designer", label: "Design", desc: "Photoshop, Illustrator, UI/UX", icon: "🎨" },
    { value: "architecture", label: "Engineering", desc: "CAD, AutoCAD, Revit", icon: "🏗️" },
  ];

// Goals available per budget — loaded from shared/budget_goals.json (see import above).
const BUDGET_GOALS = budgetGoalsData as Record<BudgetRange, UserGoal[]>;

const BUDGETS: { value: BudgetRange; label: string }[] = [
  { value: "0_1000", label: "Under €1,000" },
  { value: "1000_1500", label: "€1,000 – €1,500" },
  { value: "1500_2000", label: "€1,500 – €2,000" },
  { value: "2000_3000", label: "€2,000 – €3,000" },
  { value: "over_3000", label: "Over €3,000" },
];

const FORM_FACTORS: { value: FormFactor; label: string; desc: string }[] = [
  { value: "atx", label: "ATX", desc: "Standard — most compatible" },
  { value: "micro_atx", label: "Micro-ATX", desc: "Smaller, slightly fewer slots" },
  { value: "mini_itx", label: "Mini-ITX", desc: "Compact & portable" },
];

const CPU_BRANDS: { value: CPUBrand; label: string }[] = [
  { value: "no_preference", label: "No Preference" },
  { value: "amd", label: "AMD" },
  { value: "intel", label: "Intel" },
];

const GPU_BRANDS: { value: GPUBrand; label: string }[] = [
  { value: "no_preference", label: "No Preference" },
  { value: "nvidia", label: "NVIDIA" },
  { value: "amd", label: "AMD" },
];

const COOLING_PREFERENCES: { value: CoolingPreference; label: string; desc: string }[] = [
  { value: "no_preference", label: "No Preference", desc: "We'll pick best value" },
  { value: "liquid", label: "Liquid AIO", desc: "Quieter & better thermals" },
  { value: "air", label: "Air Cooler", desc: "Reliable & cost-effective" },
];

const COMPONENT_CATEGORIES: { value: ComponentCategory; label: string }[] = [
  { value: "cpu", label: "CPU" },
  { value: "gpu", label: "GPU" },
  { value: "motherboard", label: "Motherboard" },
  { value: "ram", label: "RAM" },
  { value: "storage", label: "Storage" },
  { value: "psu", label: "PSU" },
  { value: "case", label: "Case" },
  { value: "cooling", label: "Cooling" },
  { value: "monitor", label: "Monitor" },
  { value: "keyboard", label: "Keyboard" },
  { value: "mouse", label: "Mouse" },
];

const selectedCls = "border-obsidian bg-obsidian/10 text-obsidian";
const unselectedCls =
  "border-obsidian-border bg-obsidian-surface hover:border-obsidian-bright text-obsidian-text";

function BuildForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [notes, setNotes] = useState("");
  const [budget, setBudget] = useState<BudgetRange | null>(null);
  const [goal, setGoal] = useState<UserGoal | null>(null);
  const [formFactor, setFormFactor] = useState<FormFactor>("atx");
  const [cpuBrand, setCpuBrand] = useState<CPUBrand>("no_preference");
  const [gpuBrand, setGpuBrand] = useState<GPUBrand>("no_preference");
  const [coolingPreference, setCoolingPreference] = useState<CoolingPreference>("no_preference");
  const [includePeripherals, setIncludePeripherals] = useState(false);
  const [existingParts, setExistingParts] = useState<ComponentCategory[]>([]);

  useEffect(() => {
    const b = searchParams.get("budget") as BudgetRange | null;
    const g = searchParams.get("goal") as UserGoal | null;
    if (b && Object.keys(BUDGET_GOALS).includes(b)) {
      setBudget(b);
      if (g && BUDGET_GOALS[b].includes(g)) setGoal(g);
    }
  }, [searchParams]);

  const handleBudgetChange = (b: BudgetRange) => {
    setBudget(b);
    if (goal && !BUDGET_GOALS[b].includes(goal)) setGoal(null);
  };

  const filteredGoals = budget
    ? GOALS.filter((g) => BUDGET_GOALS[budget].includes(g.value))
    : [];

  const toggleExistingPart = (cat: ComponentCategory) => {
    setExistingParts((prev) =>
      prev.includes(cat) ? prev.filter((c) => c !== cat) : [...prev, cat]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!goal || !budget) return;
    setLoading(true);
    setError(null);
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 120_000);
    try {
      const result = await submitBuild(
        {
          goal,
          budget_range: budget,
          form_factor: formFactor,
          cpu_brand: cpuBrand,
          gpu_brand: gpuBrand,
          cooling_preference: coolingPreference,
          include_peripherals: includePeripherals,
          existing_parts: existingParts,
          notes: notes.trim() || undefined,
        },
        controller.signal
      );
      sessionStorage.setItem("build_result", JSON.stringify(result));
      router.push(`/build/${result.id}`);
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") {
        setError("The request timed out. Please try again.");
      } else {
        const msg = err instanceof Error ? err.message : "Something went wrong. Please try again.";
        setError(msg);
      }
      setLoading(false);
    } finally {
      clearTimeout(timeout);
    }
  };

  const readyToSubmit = !!budget && !!goal;
  const selectedGoalLabel = GOALS.find((g) => g.value === goal)?.label;
  const selectedBudgetLabel = BUDGETS.find((b) => b.value === budget)?.label;

  return (
    <main className="min-h-screen bg-obsidian-bg/50 text-obsidian-text py-12 px-4">
      <div className="max-w-3xl mx-auto">

        {/* Header */}
        <div className="mb-12">
          <Link href="/" className="text-obsidian-muted hover:text-obsidian-text text-xs uppercase tracking-widest transition-colors">
            &larr; Home
          </Link>
          <h1 className="font-display font-light text-5xl text-obsidian-text mt-6 mb-2">Build Your PC</h1>
          <p className="text-obsidian-muted text-sm">
            Pick your budget and use case — everything else has sensible defaults and can be skipped.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-1">

          {/* Budget */}
          <section className="bg-obsidian-surface/50 border border-obsidian-border p-8">
            <div className="flex items-baseline gap-3 mb-6">
              <h2 className="font-body font-semibold text-obsidian-text">What&apos;s your budget?</h2>
              <span className="text-xs text-obsidian uppercase tracking-wider">required</span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {BUDGETS.map((b) => (
                <button
                  key={b.value}
                  type="button"
                  onClick={() => handleBudgetChange(b.value)}
                  className={`p-4 border text-center text-sm font-body font-medium transition-all ${
                    budget === b.value ? selectedCls : unselectedCls
                  }`}
                >
                  {b.label}
                </button>
              ))}
            </div>
          </section>

          {/* Goal */}
          <section className="bg-obsidian-surface/50 border border-obsidian-border p-8">
            <div className="flex items-baseline gap-3 mb-2">
              <h2 className="font-body font-semibold text-obsidian-text">What will you use it for?</h2>
              <span className="text-xs text-obsidian uppercase tracking-wider">required</span>
            </div>
            {!budget ? (
              <p className="text-obsidian-muted text-sm mt-3">Select a budget above — your options will appear here.</p>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2 mt-6">
                {filteredGoals.map((g) => (
                  <button
                    key={g.value}
                    type="button"
                    onClick={() => setGoal(g.value)}
                    className={`p-4 border text-left transition-all ${
                      goal === g.value ? selectedCls : unselectedCls
                    }`}
                  >
                    <div className="text-2xl mb-2">{g.icon}</div>
                    <div className="font-body font-medium text-sm">{g.label}</div>
                    <div className="text-obsidian-muted text-xs mt-1">{g.desc}</div>
                  </button>
                ))}
              </div>
            )}
          </section>

          {/* Preferences */}
          <section className="bg-obsidian-surface/50 border border-obsidian-border p-8">
            <div className="flex items-baseline gap-3 mb-2">
              <h2 className="font-body font-semibold text-obsidian-text">Build preferences</h2>
              <span className="text-xs text-obsidian-muted uppercase tracking-wider">optional</span>
            </div>
            <p className="text-obsidian-muted text-sm mb-8">
              Leave at defaults and we&apos;ll pick the best value.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {[
                {
                  label: "Case Size",
                  items: FORM_FACTORS.map((f) => ({
                    key: f.value,
                    active: formFactor === f.value,
                    onClick: () => setFormFactor(f.value),
                    primary: f.label,
                    secondary: f.desc,
                  })),
                },
                {
                  label: "CPU Brand",
                  items: CPU_BRANDS.map((b) => ({
                    key: b.value,
                    active: cpuBrand === b.value,
                    onClick: () => setCpuBrand(b.value),
                    primary: b.label,
                    secondary: null,
                  })),
                },
                {
                  label: "GPU Brand",
                  items: GPU_BRANDS.map((b) => ({
                    key: b.value,
                    active: gpuBrand === b.value,
                    onClick: () => setGpuBrand(b.value),
                    primary: b.label,
                    secondary: null,
                  })),
                },
                {
                  label: "Cooling",
                  items: COOLING_PREFERENCES.map((c) => ({
                    key: c.value,
                    active: coolingPreference === c.value,
                    onClick: () => setCoolingPreference(c.value),
                    primary: c.label,
                    secondary: c.desc,
                  })),
                },
              ].map((group) => (
                <div key={group.label}>
                  <label className="text-xs text-obsidian-muted uppercase tracking-widest mb-3 block">
                    {group.label}
                  </label>
                  <div className="space-y-1.5">
                    {group.items.map((item) => (
                      <button
                        key={item.key}
                        type="button"
                        onClick={item.onClick}
                        className={`w-full p-3 border text-sm text-left transition-all ${
                          item.active ? selectedCls : unselectedCls
                        }`}
                      >
                        <div className="font-body font-medium">{item.primary}</div>
                        {item.secondary && (
                          <div className="text-obsidian-muted text-xs mt-0.5">{item.secondary}</div>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Peripherals */}
          <section>
            <label className="flex items-start gap-4 p-6 border border-obsidian-border bg-obsidian-surface hover:border-obsidian-bright cursor-pointer transition-colors">
              <input
                type="checkbox"
                checked={includePeripherals}
                onChange={(e) => setIncludePeripherals(e.target.checked)}
                className="w-4 h-4 mt-0.5 shrink-0 accent-obsidian"
              />
              <div>
                <div className="font-body font-medium text-obsidian-text">Include peripherals</div>
                <div className="text-obsidian-muted text-sm mt-0.5">
                  Add a monitor, keyboard, and mouse to the component list
                </div>
              </div>
            </label>
          </section>

          {/* Existing Parts */}
          <section className="bg-obsidian-surface/50 border border-obsidian-border p-8">
            <h2 className="font-body font-semibold text-obsidian-text mb-1">Parts you already own</h2>
            <p className="text-obsidian-muted text-sm mb-6">
              Tag anything you already have — we&apos;ll build around it and skip recommending those parts.
            </p>
            <div className="flex flex-wrap gap-2">
              {COMPONENT_CATEGORIES.map((c) => (
                <button
                  key={c.value}
                  type="button"
                  onClick={() => toggleExistingPart(c.value)}
                  className={`px-4 py-2 text-sm border transition-all font-body ${
                    existingParts.includes(c.value) ? selectedCls : unselectedCls
                  }`}
                >
                  {c.label}
                </button>
              ))}
            </div>
          </section>

          {/* Notes */}
          <section className="bg-obsidian-surface/50 border border-obsidian-border p-8">
            <h2 className="font-body font-semibold text-obsidian-text mb-1">Anything else?</h2>
            <p className="text-obsidian-muted text-sm mb-5">
              Optional — noise levels, RGB, a case you already own, expansion plans, etc.
            </p>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Silent build preferred, no RGB, I already have a Fractal case…"
              maxLength={500}
              rows={3}
              className="w-full bg-obsidian-raised border border-obsidian-border px-4 py-3 text-obsidian-text placeholder-obsidian-muted-light focus:outline-none focus:border-obsidian resize-none transition-all text-sm font-body"
            />
            <p className="text-obsidian-muted-light text-xs mt-1 text-right font-mono">
              {notes.length}/500
            </p>
          </section>

          {/* Submit */}
          <div className="pt-4">
            {readyToSubmit && !loading && (
              <p className="text-center text-obsidian-muted text-sm mb-4">
                Generating:{" "}
                <span className="text-obsidian-text font-medium">{selectedGoalLabel}</span>
                {" · "}
                <span className="text-obsidian-text font-medium">{selectedBudgetLabel}</span>
              </p>
            )}
            <button
              type="submit"
              disabled={!readyToSubmit || loading}
              className={`w-full py-4 text-base font-body font-semibold transition-all ${
                readyToSubmit && !loading
                  ? "btn-shimmer bg-obsidian text-obsidian-bg hover:brightness-110 hover:shadow-[0_0_25px_rgba(251,191,36,0.25)]"
                  : "bg-obsidian-surface/50 border border-obsidian-border text-obsidian-muted cursor-not-allowed"
              }`}
            >
              {loading
                ? "Building your component list — usually 30–60 seconds…"
                : "Build My PC \u2192"}
            </button>
            {!readyToSubmit && !loading && (
              <p className="text-center text-obsidian-muted text-sm mt-3">
                {!budget ? "Select a budget to continue" : "Select a use case to continue"}
              </p>
            )}
          </div>

        </form>
      </div>

      {error && <ErrorModal message={error} onDismiss={() => setError(null)} />}
    </main>
  );
}

export default function BuildPage() {
  return (
    <Suspense>
      <BuildForm />
    </Suspense>
  );
}
