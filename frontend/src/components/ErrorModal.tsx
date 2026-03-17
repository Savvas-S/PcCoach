"use client";

import { useEffect } from "react";

type ErrorModalProps = {
  message: string;
  onDismiss: () => void;
};

export function ErrorModal({ message, onDismiss }: ErrorModalProps) {
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onDismiss();
    };
    document.addEventListener("keydown", handleEsc);
    return () => document.removeEventListener("keydown", handleEsc);
  }, [onDismiss]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm px-4"
      onClick={onDismiss}
    >
      <div
        className="relative bg-obsidian-surface border border-obsidian-border rounded-lg w-full max-w-sm overflow-hidden shadow-[0_8px_40px_rgba(0,0,0,0.5)]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Gold accent line */}
        <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-obsidian/60 to-transparent" />

        {/* Icon */}
        <div className="flex justify-center pt-8 pb-2">
          <div className="w-12 h-12 rounded-full bg-amber-900/20 border border-amber-700/30 flex items-center justify-center">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="w-6 h-6 text-amber-400"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={1.5}
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 9v4m0 4h.01" />
              <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
            </svg>
          </div>
        </div>

        {/* Heading */}
        <h2 className="text-center font-display text-xl text-obsidian-text px-6 pt-2 pb-1">
          Something went wrong
        </h2>

        {/* Body */}
        <div className="px-8 pt-1 pb-6">
          <p className="text-center text-obsidian-muted text-sm leading-relaxed">
            {message}
          </p>
        </div>

        {/* Divider */}
        <div className="mx-6 h-px bg-obsidian-border" />

        {/* Footer */}
        <div className="px-6 py-5">
          <button
            onClick={onDismiss}
            className="w-full py-3 rounded bg-obsidian text-obsidian-bg text-sm font-body font-semibold hover:brightness-110 transition-all"
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
}
