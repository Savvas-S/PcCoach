"use client";

import { useState, useEffect, useRef, useMemo, useCallback } from "react";
import type { BuildProgress } from "@/lib/api";

interface BuildLoadingProps {
  goalLabel: string;
  budgetLabel: string;
  includePeripherals: boolean;
  progress: BuildProgress | null;
}

const CORE_SLOTS = [
  { key: "cpu", label: "Processor", icon: "cpu" },
  { key: "motherboard", label: "Motherboard", icon: "board" },
  { key: "gpu", label: "Graphics", icon: "gpu" },
  { key: "ram", label: "Memory", icon: "ram" },
  { key: "storage", label: "Storage", icon: "ssd" },
  { key: "psu", label: "Power", icon: "psu" },
  { key: "case", label: "Case", icon: "case" },
  { key: "cooling", label: "Cooling", icon: "cool" },
];

const PERIPHERAL_SLOTS = [
  { key: "monitor", label: "Monitor", icon: "mon" },
  { key: "keyboard", label: "Keyboard", icon: "key" },
  { key: "mouse", label: "Mouse", icon: "mouse" },
];

const PHASE_LABELS: Record<string, { label: string; sub: string }> = {
  scouting: { label: "Scouting the catalog", sub: "Scanning available components" },
  selecting: { label: "Selecting components", sub: "Refining choices with filters" },
  validating: { label: "Checking compatibility", sub: "Verifying sockets, DDR, form factor, power" },
  repairing: { label: "Fixing compatibility", sub: "Adjusting component selection" },
};

const INITIAL_PHASE = { label: "Analyzing requirements", sub: "Parsing your preferences" };

function SlotIcon({ icon, filled }: { icon: string; filled: boolean }) {
  const color = filled ? "var(--gold)" : "var(--muted-light)";
  const common = { width: 22, height: 22, viewBox: "0 0 24 24", fill: "none", stroke: color, strokeWidth: 1.5, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };

  switch (icon) {
    case "cpu":
      return (
        <svg {...common}>
          <rect x="4" y="4" width="16" height="16" rx="2" />
          <rect x="9" y="9" width="6" height="6" />
          <path d="M9 1v3M15 1v3M9 20v3M15 20v3M1 9h3M1 15h3M20 9h3M20 15h3" />
        </svg>
      );
    case "board":
      return (
        <svg {...common}>
          <rect x="2" y="2" width="20" height="20" rx="1" />
          <rect x="6" y="5" width="5" height="4" rx="0.5" />
          <path d="M6 13h12M6 16h8" />
          <circle cx="17" cy="7" r="2" />
        </svg>
      );
    case "gpu":
      return (
        <svg {...common}>
          <rect x="1" y="6" width="22" height="12" rx="2" />
          <path d="M5 6V4M9 6V4M13 6V4" />
          <circle cx="17" cy="12" r="3" />
          <circle cx="8" cy="12" r="2" />
        </svg>
      );
    case "ram":
      return (
        <svg {...common}>
          <rect x="3" y="4" width="18" height="16" rx="1" />
          <path d="M7 4v16M11 4v16M15 4v16M19 4v16" />
          <path d="M9 20v2M15 20v2" />
        </svg>
      );
    case "ssd":
      return (
        <svg {...common}>
          <rect x="2" y="4" width="20" height="16" rx="2" />
          <circle cx="12" cy="12" r="4" />
          <circle cx="12" cy="12" r="1" />
        </svg>
      );
    case "psu":
      return (
        <svg {...common}>
          <rect x="2" y="4" width="20" height="16" rx="2" />
          <circle cx="12" cy="12" r="3" />
          <path d="M12 6v2M12 16v2M6 12h2M16 12h2" />
        </svg>
      );
    case "case":
      return (
        <svg {...common}>
          <rect x="5" y="1" width="14" height="22" rx="2" />
          <circle cx="12" cy="6" r="2" />
          <path d="M9 12h6M9 15h6" />
          <circle cx="12" cy="20" r="1" />
        </svg>
      );
    case "cool":
      return (
        <svg {...common}>
          <circle cx="12" cy="12" r="10" />
          <path d="M12 2v4M12 18v4M2 12h4M18 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M5.6 18.4l2.8-2.8M15.6 8.4l2.8-2.8" />
        </svg>
      );
    case "mon":
      return (
        <svg {...common}>
          <rect x="2" y="3" width="20" height="14" rx="2" />
          <path d="M8 21h8M12 17v4" />
        </svg>
      );
    case "key":
      return (
        <svg {...common}>
          <rect x="1" y="6" width="22" height="12" rx="2" />
          <path d="M5 10h1M8 10h1M11 10h2M16 10h1M19 10h1M6 14h12" />
        </svg>
      );
    case "mouse":
      return (
        <svg {...common}>
          <rect x="6" y="2" width="12" height="20" rx="6" />
          <path d="M12 2v7M6 9h12" />
        </svg>
      );
    default:
      return null;
  }
}

export function BuildLoadingScreen({
  goalLabel,
  budgetLabel,
  includePeripherals,
  progress,
}: BuildLoadingProps) {
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef(Date.now());

  // Staggered reveal: real data feeds a queue, UI reveals one-by-one
  const [revealedSlots, setRevealedSlots] = useState<Set<string>>(
    new Set(),
  );
  const queueRef = useRef<string[]>([]);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const slots = useMemo(
    () =>
      includePeripherals
        ? [...CORE_SLOTS, ...PERIPHERAL_SLOTS]
        : CORE_SLOTS,
    [includePeripherals],
  );

  // Elapsed timer (client-side, always accurate)
  useEffect(() => {
    const id = setInterval(() => {
      setElapsed(
        Math.floor((Date.now() - startRef.current) / 1000),
      );
    }, 1000);
    return () => clearInterval(id);
  }, []);

  // Drain one item from the queue every REVEAL_INTERVAL_MS
  const REVEAL_INTERVAL_MS = 350;

  const drainOne = useCallback(() => {
    const next = queueRef.current.shift();
    if (next) {
      setRevealedSlots((prev) => new Set(prev).add(next));
      timerRef.current = setTimeout(drainOne, REVEAL_INTERVAL_MS);
    } else {
      timerRef.current = null;
    }
  }, []);

  // When progress arrives, push new categories onto the queue
  useEffect(() => {
    if (!progress) return;
    const allSeen = new Set([
      ...(progress.categories_scouted ?? []),
      ...(progress.categories_queried ?? []),
    ]);
    // Add any new categories not yet revealed or queued
    const queued = new Set(queueRef.current);
    for (const cat of allSeen) {
      if (!revealedSlots.has(cat) && !queued.has(cat)) {
        queueRef.current.push(cat);
      }
    }
    // If validating/repairing, queue ALL remaining slots
    if (
      progress.phase === "validating" ||
      progress.phase === "repairing"
    ) {
      for (const slot of slots) {
        if (
          !revealedSlots.has(slot.key) &&
          !queued.has(slot.key) &&
          !queueRef.current.includes(slot.key)
        ) {
          queueRef.current.push(slot.key);
        }
      }
    }
    // Start draining if not already running
    if (timerRef.current === null && queueRef.current.length > 0) {
      drainOne();
    }
  }, [progress, slots, drainOne]); // eslint-disable-line react-hooks/exhaustive-deps

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  // Phase label
  const phaseInfo = progress
    ? (PHASE_LABELS[progress.phase] ?? INITIAL_PHASE)
    : INITIAL_PHASE;

  // Progress bar — based on revealed count + phase
  const progressPct = useMemo(() => {
    if (!progress) return 0.03;
    const { phase } = progress;
    const total = slots.length;
    const revealed = revealedSlots.size;
    const ratio = total > 0 ? revealed / total : 0;

    if (phase === "scouting") return 0.05 + ratio * 0.35;
    if (phase === "selecting") return 0.40 + ratio * 0.20;
    if (phase === "validating") return 0.65 + ratio * 0.20;
    if (phase === "repairing") return 0.65 + ratio * 0.15;
    return 0.10;
  }, [progress, slots.length, revealedSlots.size]);

  const formatTime = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}:${sec.toString().padStart(2, "0")}`;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-obsidian-bg" role="status" aria-label="Building your PC recommendation">
      {/* Atmospheric grain overlay */}
      <div
        className="absolute inset-0 opacity-[0.03] pointer-events-none"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")`,
        }}
      />

      {/* Radial glow */}
      <div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full pointer-events-none"
        style={{
          background:
            "radial-gradient(circle, rgba(201,168,76,0.06) 0%, rgba(201,168,76,0.02) 40%, transparent 70%)",
        }}
      />

      <div className="relative w-full max-w-2xl mx-auto px-6">
        {/* Header */}
        <div className="text-center mb-12 build-load-fade-in">
          <p className="text-obsidian-muted text-xs uppercase tracking-[0.25em] mb-4 font-mono">
            Assembling
          </p>
          <h1 className="font-display font-light text-4xl sm:text-5xl text-obsidian-text mb-3">
            {goalLabel}
          </h1>
          <p className="text-obsidian-muted text-sm font-body">{budgetLabel}</p>
        </div>

        {/* Component grid */}
        <div className="grid grid-cols-4 gap-2 sm:gap-3 mb-12">
          {slots.map((slot) => {
            const filled = revealedSlots.has(slot.key);
            const visible = progress !== null || elapsed >= 1;

            return (
              <div
                key={slot.key}
                className="relative"
                style={{
                  opacity: visible ? 1 : 0,
                  transform: visible ? "translateY(0)" : "translateY(12px)",
                  transition: "opacity 0.5s ease, transform 0.5s ease",
                }}
              >
                <div
                  className={`
                    relative border p-3 sm:p-4 flex flex-col items-center gap-2 transition-all duration-700
                    ${filled
                      ? "border-obsidian/50 bg-obsidian/[0.07]"
                      : "border-obsidian-border bg-obsidian-surface/40"
                    }
                  `}
                >
                  {/* Scanning line when not yet filled */}
                  {visible && !filled && (
                    <div className="absolute inset-0 overflow-hidden pointer-events-none">
                      <div className="build-scan-line" />
                    </div>
                  )}

                  <SlotIcon icon={slot.icon} filled={filled} />
                  <span
                    className={`text-[10px] sm:text-xs font-mono uppercase tracking-wider transition-colors duration-700 ${
                      filled ? "text-obsidian" : "text-obsidian-muted-light"
                    }`}
                  >
                    {slot.label}
                  </span>

                  {/* Check mark */}
                  {filled && (
                    <div className="absolute -top-1 -right-1 w-4 h-4 bg-obsidian rounded-full flex items-center justify-center build-slot-check" aria-hidden="true">
                      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="var(--bg)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M5 12l5 5L20 7" />
                      </svg>
                    </div>
                  )}
                  {filled && <span className="sr-only">{slot.label} selected</span>}
                </div>
              </div>
            );
          })}
        </div>

        {/* Phase + progress */}
        <div className="space-y-4 build-load-fade-in" style={{ animationDelay: "0.4s" }}>
          <div className="text-center" aria-live="polite" aria-atomic="true">
            <p className="text-obsidian-text text-sm font-body font-medium">
              {phaseInfo.label}
            </p>
            <p className="text-obsidian-muted-light text-xs font-body mt-1">
              {phaseInfo.sub}
            </p>
          </div>

          {/* Progress bar */}
          <div
            className="relative h-[2px] bg-obsidian-border rounded-full overflow-hidden"
            role="progressbar"
            aria-valuenow={Math.round(progressPct * 100)}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Build progress"
          >
            <div
              className="absolute inset-y-0 left-0 bg-obsidian rounded-full transition-[width] duration-1000 ease-out"
              style={{ width: `${progressPct * 100}%` }}
            />
            <div
              className="absolute inset-y-0 left-0 rounded-full build-bar-glow"
              style={{ width: `${progressPct * 100}%` }}
            />
          </div>

          {/* Timer */}
          <p className="text-center text-obsidian-muted-light text-xs font-mono tabular-nums">
            {formatTime(elapsed)}
          </p>
        </div>
      </div>
    </div>
  );
}
