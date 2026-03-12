"use client";

import { useEffect, useState } from "react";

type ToastProps = {
  message: string;
  onDismiss: () => void;
  autoDismissMs?: number;
};

export function Toast({ message, onDismiss, autoDismissMs = 7000 }: ToastProps) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const frame = requestAnimationFrame(() => setVisible(true));
    const timer = setTimeout(onDismiss, autoDismissMs);
    return () => {
      cancelAnimationFrame(frame);
      clearTimeout(timer);
    };
  }, [onDismiss, autoDismissMs]);

  return (
    <div
      className={`fixed bottom-6 left-1/2 -translate-x-1/2 z-50 transition-all duration-300 ease-out ${
        visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-3"
      }`}
    >
      <div className="flex items-start gap-3 bg-gray-800 border border-red-500/40 rounded-xl px-4 py-3.5 shadow-2xl w-[calc(100vw-2rem)] max-w-md">
        <span className="text-red-400 shrink-0 mt-0.5">
          <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        </span>
        <p className="text-sm text-gray-100 leading-snug flex-1">{message}</p>
        <button
          onClick={onDismiss}
          aria-label="Dismiss"
          className="text-gray-500 hover:text-white transition-colors shrink-0 mt-0.5"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        </button>
      </div>
    </div>
  );
}
