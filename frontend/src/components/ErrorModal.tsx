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
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4"
      onClick={onDismiss}
    >
      <div
        className="bg-obsidian-surface border border-obsidian-border w-full max-w-md"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center gap-3 px-6 pt-6 pb-4">
          <div className="w-10 h-10 rounded-full bg-red-900/30 border border-red-800/40 flex items-center justify-center shrink-0">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="w-5 h-5 text-red-400"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <h2 className="font-body font-semibold text-obsidian-text text-lg">
            Something went wrong
          </h2>
        </div>

        {/* Body */}
        <div className="px-6 pb-4">
          <p className="text-obsidian-muted text-sm leading-relaxed">
            {message}
          </p>
        </div>

        {/* Footer */}
        <div className="px-6 pb-6 pt-2">
          <button
            onClick={onDismiss}
            className="w-full py-3 bg-obsidian text-obsidian-bg text-sm font-body font-semibold hover:brightness-110 transition-all"
          >
            Got it
          </button>
        </div>
      </div>
    </div>
  );
}
