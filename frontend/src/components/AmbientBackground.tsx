"use client";

import { useEffect, useRef } from "react";

export function AmbientBackground() {
  const auroraRef = useRef<HTMLDivElement>(null);
  const orbsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (mq.matches) return;

    let ticking = false;
    const onScroll = () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          const y = Math.min(window.scrollY, window.innerHeight);
          if (auroraRef.current) auroraRef.current.style.transform = `translateY(${y * 0.03}px)`;
          if (orbsRef.current) orbsRef.current.style.transform = `translateY(${y * 0.06}px)`;
          ticking = false;
        });
        ticking = true;
      }
    };

    window.addEventListener("scroll", onScroll, { passive: true });

    const onMotionChange = (e: MediaQueryListEvent) => {
      if (e.matches) {
        window.removeEventListener("scroll", onScroll);
        [auroraRef, orbsRef].forEach((ref) => {
          if (ref.current) ref.current.style.transform = "";
        });
      } else {
        window.addEventListener("scroll", onScroll, { passive: true });
      }
    };
    mq.addEventListener("change", onMotionChange);

    return () => {
      window.removeEventListener("scroll", onScroll);
      mq.removeEventListener("change", onMotionChange);
    };
  }, []);

  return (
    <div className="fixed inset-0 z-0 bg-obsidian-bg pointer-events-none overflow-hidden" aria-hidden="true">
      {/* ── Aurora layers (dimmed ~8%) ── */}
      <div ref={auroraRef} className="absolute inset-0">
        <div
          className="absolute -inset-1/2 animate-aurora-1"
          style={{ background: "radial-gradient(ellipse 50% 40% at 60% 20%, rgba(217,119,6,0.14) 0%, transparent 70%)" }}
        />
        <div
          className="absolute -inset-1/2 animate-aurora-2"
          style={{ background: "radial-gradient(ellipse 45% 50% at 30% 70%, rgba(217,119,6,0.11) 0%, transparent 65%)" }}
        />
        <div
          className="absolute -inset-1/2 animate-aurora-1 [animation-delay:-7s]"
          style={{ background: "radial-gradient(ellipse 40% 35% at 70% 60%, rgba(217,119,6,0.09) 0%, transparent 60%)" }}
        />
      </div>

      {/* ── Floating orbs (dimmed ~8%) ── */}
      <div ref={orbsRef} className="absolute inset-0 will-change-transform">
        <div
          className="absolute top-[15%] left-[10%] w-72 h-72 rounded-full blur-3xl animate-float-1"
          style={{ background: "radial-gradient(circle, rgba(217,119,6,0.12), transparent 70%)" }}
        />
        <div
          className="absolute bottom-[20%] right-[8%] w-56 h-56 rounded-full blur-3xl animate-float-2"
          style={{ background: "radial-gradient(circle, rgba(217,119,6,0.10), transparent 70%)" }}
        />
        <div
          className="absolute top-[50%] left-[55%] w-40 h-40 rounded-full blur-2xl animate-float-3"
          style={{ background: "radial-gradient(circle, rgba(217,119,6,0.09), transparent 65%)" }}
        />
      </div>
    </div>
  );
}
