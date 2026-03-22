# PcCoach — Session Progress Log

## Current State

The project is **feature-complete for MVP** on the core build flow: users submit preferences via the form, Claude runs an agentic tool loop to select compatible components from a 277-product catalog, results stream via SSE with real-time progress, and affiliate links point to Amazon.de. Input/output guardrails, rate limiting, caching, and compatibility validation are all in place with a comprehensive test suite (7 files, 50+ tests).

**What's missing for launch:** affiliate compliance fixes (fake phone number, per-page disclosures, footer text), SEO gaps (favicon, OG meta tags on static pages), content pages (examples, guides index), and catalog gaps (no mini-ITX cases, hardcoded peripherals, stale prices). The Telegram bot scaffold exists but is not wired end-to-end.

## Last Session

- **Date:** 2026-03-22
- **Work done:** Initial harness setup — added session rules to CLAUDE.md, created features.json (40 features: 24 passing, 16 failing), progress.md, init.sh, orchestrator.py
- **Branch:** claude/harness-init-jscef
- **Commit:** (filled after commit)

## Next Priority

**F027** — Fix fake phone number on contact page. This is the first compliance blocker in TO-DO.md Part 1 and is trivial to fix (remove or replace +357 25 000 000). After that, proceed to F023 (per-page affiliate disclosure) and F028 (footer disclosure text).

## Known Issues

1. **Fake phone number** on contact page (+357 25 000 000) — compliance risk
2. **No favicon** — site shows browser default icon
3. **No mini-ITX cases** in catalog — mini-ITX builds will fail at case selection
4. **Peripherals hardcoded** in seed.py with unverified ASINs — may link to wrong products
5. **Prices are stale** — snapshot from scrape date, no automated refresh
6. **Telegram bot** — scaffold exists but not integration-tested
7. **Toast component** built but never rendered anywhere
8. **price.ts discrepancy** — CLAUDE.md documents step-based price ranges but code uses simple formatting
