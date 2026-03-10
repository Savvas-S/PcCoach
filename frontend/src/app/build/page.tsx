"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { submitBuild } from "@/lib/api";
import type {
  UserGoal,
  BudgetRange,
  FormFactor,
  CPUBrand,
  GPUBrand,
  CoolingPreference,
  ComponentCategory,
} from "@/lib/api";

const GOALS: { value: UserGoal; label: string; desc: string; icon: string }[] =
  [
    {
      value: "high_end_gaming",
      label: "High-End Gaming",
      desc: "4K, max settings, 144fps+",
      icon: "🎮",
    },
    {
      value: "mid_range_gaming",
      label: "Mid-Range Gaming",
      desc: "1080p/1440p, high settings",
      icon: "🕹️",
    },
    {
      value: "low_end_gaming",
      label: "Budget Gaming",
      desc: "1080p, medium settings",
      icon: "👾",
    },
    {
      value: "light_work",
      label: "Everyday Use",
      desc: "Office, web, video calls",
      icon: "💼",
    },
    {
      value: "heavy_work",
      label: "Power User",
      desc: "Video editing, rendering, VMs",
      icon: "⚙️",
    },
    {
      value: "designer",
      label: "Design",
      desc: "Photoshop, Illustrator, UI/UX",
      icon: "🎨",
    },
    {
      value: "architecture",
      label: "Engineering",
      desc: "CAD, AutoCAD, Revit",
      icon: "🏗️",
    },
  ];

// Goals available per budget — mirrors the Telegram bot logic
const BUDGET_GOALS: Record<BudgetRange, UserGoal[]> = {
  "0_1000":    ["low_end_gaming", "light_work"],
  "1000_1500": ["mid_range_gaming", "light_work", "heavy_work", "designer", "architecture"],
  "1500_2000": ["high_end_gaming", "mid_range_gaming", "light_work", "heavy_work", "designer", "architecture"],
  "2000_3000": ["high_end_gaming", "heavy_work", "designer", "architecture"],
  "over_3000": ["high_end_gaming", "heavy_work", "designer", "architecture"],
};

const BUDGETS: { value: BudgetRange; label: string }[] = [
  { value: "0_1000", label: "Under €1,000" },
  { value: "1000_1500", label: "€1,000 – €1,500" },
  { value: "1500_2000", label: "€1,500 – €2,000" },
  { value: "2000_3000", label: "€2,000 – €3,000" },
  { value: "over_3000", label: "Over €3,000" },
];

const FORM_FACTORS: { value: FormFactor; label: string }[] = [
  { value: "atx", label: "ATX (Full Size)" },
  { value: "micro_atx", label: "Micro-ATX" },
  { value: "mini_itx", label: "Mini-ITX (Compact)" },
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

export default function BuildPage() {
  const router = useRouter();
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

  const handleBudgetChange = (b: BudgetRange) => {
    setBudget(b);
    // Clear goal if it's no longer valid for the new budget
    if (goal && !BUDGET_GOALS[b].includes(goal)) {
      setGoal(null);
    }
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
      const msg =
        err instanceof Error ? err.message : "Something went wrong. Please try again.";
      setError(msg);
      setLoading(false);
    } finally {
      clearTimeout(timeout);
    }
  };

  return (
    <main className="min-h-screen bg-gray-900 text-white py-12 px-4">
      <div className="max-w-3xl mx-auto">
        <div className="mb-10">
          <Link href="/" className="text-gray-400 hover:text-white text-sm">
            &larr; Back
          </Link>
          <h1 className="text-3xl font-bold mt-4">Configure Your Build</h1>
          <p className="text-gray-400 mt-1">
            Tell us what you need and we&apos;ll recommend the perfect
            components.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-12">
          {/* Budget — first, so goals can be filtered */}
          <section>
            <h2 className="text-lg font-semibold mb-4">
              What&apos;s your budget?
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {BUDGETS.map((b) => (
                <button
                  key={b.value}
                  type="button"
                  onClick={() => handleBudgetChange(b.value)}
                  className={`p-4 rounded-xl border text-center font-medium transition-all ${
                    budget === b.value
                      ? "border-blue-500 bg-blue-500/10 text-blue-400"
                      : "border-gray-700 bg-gray-800 hover:border-gray-500 text-white"
                  }`}
                >
                  {b.label}
                </button>
              ))}
            </div>
          </section>

          {/* Goal — filtered based on selected budget */}
          <section>
            <h2 className="text-lg font-semibold mb-1">
              What will you use it for?
            </h2>
            {!budget ? (
              <p className="text-gray-500 text-sm mt-2">
                Select a budget above to see available options.
              </p>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mt-4">
                {filteredGoals.map((g) => (
                  <button
                    key={g.value}
                    type="button"
                    onClick={() => setGoal(g.value)}
                    className={`p-4 rounded-xl border text-left transition-all ${
                      goal === g.value
                        ? "border-blue-500 bg-blue-500/10"
                        : "border-gray-700 bg-gray-800 hover:border-gray-500"
                    }`}
                  >
                    <div className="text-2xl mb-2">{g.icon}</div>
                    <div className="font-medium text-sm">{g.label}</div>
                    <div className="text-gray-400 text-xs mt-1">{g.desc}</div>
                  </button>
                ))}
              </div>
            )}
          </section>

          {/* Preferences */}
          <section>
            <h2 className="text-lg font-semibold mb-4">Preferences</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div>
                <label className="text-sm text-gray-400 mb-2 block">
                  Form Factor
                </label>
                <div className="space-y-2">
                  {FORM_FACTORS.map((f) => (
                    <button
                      key={f.value}
                      type="button"
                      onClick={() => setFormFactor(f.value)}
                      className={`w-full p-3 rounded-lg border text-sm text-left transition-all ${
                        formFactor === f.value
                          ? "border-blue-500 bg-blue-500/10"
                          : "border-gray-700 bg-gray-800 hover:border-gray-500"
                      }`}
                    >
                      {f.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-sm text-gray-400 mb-2 block">
                  CPU Brand
                </label>
                <div className="space-y-2">
                  {CPU_BRANDS.map((b) => (
                    <button
                      key={b.value}
                      type="button"
                      onClick={() => setCpuBrand(b.value)}
                      className={`w-full p-3 rounded-lg border text-sm text-left transition-all ${
                        cpuBrand === b.value
                          ? "border-blue-500 bg-blue-500/10"
                          : "border-gray-700 bg-gray-800 hover:border-gray-500"
                      }`}
                    >
                      {b.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-sm text-gray-400 mb-2 block">
                  GPU Brand
                </label>
                <div className="space-y-2">
                  {GPU_BRANDS.map((b) => (
                    <button
                      key={b.value}
                      type="button"
                      onClick={() => setGpuBrand(b.value)}
                      className={`w-full p-3 rounded-lg border text-sm text-left transition-all ${
                        gpuBrand === b.value
                          ? "border-blue-500 bg-blue-500/10"
                          : "border-gray-700 bg-gray-800 hover:border-gray-500"
                      }`}
                    >
                      {b.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-sm text-gray-400 mb-2 block">
                  Cooling
                </label>
                <div className="space-y-2">
                  {COOLING_PREFERENCES.map((c) => (
                    <button
                      key={c.value}
                      type="button"
                      onClick={() => setCoolingPreference(c.value)}
                      className={`w-full p-3 rounded-lg border text-sm text-left transition-all ${
                        coolingPreference === c.value
                          ? "border-blue-500 bg-blue-500/10"
                          : "border-gray-700 bg-gray-800 hover:border-gray-500"
                      }`}
                    >
                      <div>{c.label}</div>
                      <div className="text-gray-400 text-xs mt-0.5">{c.desc}</div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </section>

          {/* Peripherals */}
          <section>
            <h2 className="text-lg font-semibold mb-4">Options</h2>
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={includePeripherals}
                onChange={(e) => setIncludePeripherals(e.target.checked)}
                className="w-5 h-5 rounded accent-blue-500"
              />
              <div>
                <div className="font-medium">Include Peripherals</div>
                <div className="text-gray-400 text-sm">
                  Add monitor, keyboard, and mouse to the build
                </div>
              </div>
            </label>
          </section>

          {/* Existing Parts */}
          <section>
            <h2 className="text-lg font-semibold mb-1">
              Parts You Already Own
            </h2>
            <p className="text-gray-400 text-sm mb-4">
              We&apos;ll skip recommending these.
            </p>
            <div className="flex flex-wrap gap-2">
              {COMPONENT_CATEGORIES.map((c) => (
                <button
                  key={c.value}
                  type="button"
                  onClick={() => toggleExistingPart(c.value)}
                  className={`px-3 py-1.5 rounded-lg text-sm border transition-all ${
                    existingParts.includes(c.value)
                      ? "border-blue-500 bg-blue-500/10 text-blue-400"
                      : "border-gray-700 bg-gray-800 hover:border-gray-500 text-gray-300"
                  }`}
                >
                  {c.label}
                </button>
              ))}
            </div>
          </section>


          {/* Notes */}
          <section>
            <h2 className="text-lg font-semibold mb-1">Additional Notes</h2>
            <p className="text-gray-400 text-sm mb-4">
              Optional — specific requirements, component preferences, or anything else we should know.
            </p>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Prefer quiet components, already have a monitor, want good airflow..."
              maxLength={500}
              rows={3}
              className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 resize-none"
            />
            <p className="text-gray-600 text-xs mt-1 text-right">{notes.length}/500</p>
          </section>

          {error && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl p-4 text-sm">
              {error}
            </div>
          )}

          <div>
            <button
              type="submit"
              disabled={!goal || !budget || loading}
              className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 disabled:cursor-not-allowed text-white font-semibold py-4 rounded-xl text-lg transition-colors"
            >
              {loading ? "Generating your build… this may take ~30s" : "Build My PC \u2192"}
            </button>
            {(!goal || !budget) && !loading && (
              <p className="text-center text-gray-500 text-sm mt-2">
                {!budget
                  ? "Select a budget to continue"
                  : "Select a goal to continue"}
              </p>
            )}
          </div>
        </form>
      </div>
    </main>
  );
}
