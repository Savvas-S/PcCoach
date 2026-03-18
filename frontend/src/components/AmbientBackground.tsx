"use client";

import { useEffect, useRef } from "react";

/* ── Deterministic particle positions (SSR-safe, no Math.random) ── */
const PARTICLES = Array.from({ length: 25 }, (_, i) => ({
  left: `${(i * 37 + 13) % 100}%`,
  top: `${(i * 53 + 7) % 100}%`,
  size: 1 + (i % 3),
  opacity: 0.2 + (i % 4) * 0.1,
  duration: 24 + (i % 8) * 6,
  delay: -(i * 2.7),
  anim: (i % 3) + 1,
}));

export function AmbientBackground() {
  const auroraRef = useRef<HTMLDivElement>(null);
  const orbsRef = useRef<HTMLDivElement>(null);
  const particlesRef = useRef<HTMLDivElement>(null);

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
          if (particlesRef.current) particlesRef.current.style.transform = `translateY(${y * 0.04}px)`;
          ticking = false;
        });
        ticking = true;
      }
    };

    window.addEventListener("scroll", onScroll, { passive: true });

    const onMotionChange = (e: MediaQueryListEvent) => {
      if (e.matches) {
        window.removeEventListener("scroll", onScroll);
        [auroraRef, orbsRef, particlesRef].forEach((ref) => {
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
      {/* ── Aurora layers ── */}
      <div ref={auroraRef} className="absolute inset-0">
        <div
          className="absolute -inset-1/2 animate-aurora-1"
          style={{ background: "radial-gradient(ellipse 50% 40% at 60% 20%, rgba(217,119,6,0.14) 0%, transparent 70%)" }}
        />
        <div
          className="absolute -inset-1/2 animate-aurora-2"
          style={{ background: "radial-gradient(ellipse 45% 50% at 30% 70%, rgba(217,119,6,0.10) 0%, transparent 65%)" }}
        />
        <div
          className="absolute -inset-1/2 animate-aurora-1 [animation-delay:-7s]"
          style={{ background: "radial-gradient(ellipse 40% 35% at 70% 60%, rgba(217,119,6,0.08) 0%, transparent 60%)" }}
        />
      </div>

      {/* ── Floating orbs ── */}
      <div ref={orbsRef} className="absolute inset-0 will-change-transform">
        <div
          className="absolute top-[15%] left-[10%] w-72 h-72 rounded-full blur-3xl animate-float-1"
          style={{ background: "radial-gradient(circle, rgba(217,119,6,0.12), transparent 70%)" }}
        />
        <div
          className="absolute bottom-[20%] right-[8%] w-56 h-56 rounded-full blur-3xl animate-float-2"
          style={{ background: "radial-gradient(circle, rgba(217,119,6,0.09), transparent 70%)" }}
        />
        <div
          className="absolute top-[50%] left-[55%] w-40 h-40 rounded-full blur-2xl animate-float-3"
          style={{ background: "radial-gradient(circle, rgba(217,119,6,0.07), transparent 65%)" }}
        />
      </div>

      {/* ── Particle field ── */}
      <div ref={particlesRef} className="absolute inset-0">
        {PARTICLES.map((p, i) => (
          <div
            key={i}
            className="absolute rounded-full"
            style={{
              left: p.left,
              top: p.top,
              width: p.size,
              height: p.size,
              backgroundColor: `rgba(217, 119, 6, ${p.opacity})`,
              boxShadow: `0 0 ${p.size * 3}px rgba(217, 119, 6, ${p.opacity * 0.6})`,
              animation: `float-${p.anim} ${p.duration}s ease-in-out infinite`,
              animationDelay: `${p.delay}s`,
            }}
          />
        ))}
      </div>
    </div>
  );
}
