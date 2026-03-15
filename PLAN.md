# Agentic Framework Implementation Plan

## Overview

Replace the current single-shot Claude call with a **catalog-driven architecture**:
- **DB is the catalog** — real components, real prices, real affiliate links
- **Claude is the brain** — picks the optimal combination from pre-filtered candidates
- **No hallucinated products** — Claude only sees what's actually in stock

**Target branch**: `development` (PR from `claude/agentic-framework-evaluation-4KTyz` → `development`)

---

## Current State (as of 2026-03-15)

### Completed

- [x] **Step 1**: DB Schema — `components` + `affiliate_links` tables + migration
- [x] **Step 2**: Seed data — replaced hardcoded `SEED_COMPONENTS` with JSON-driven catalog
- [x] **Step 3**: `CatalogService` — queries DB for candidates filtered by brand, socket, form factor, cooling
- [x] **Step 4**: `ClaudeService.generate_build()` — catalog-driven prompt with `_format_candidates()`
- [x] **Step 5**: System prompt updated with candidate selection instructions
- [x] **Step 6**: DB session passed through to `generate_build()`
- [x] **Scraper integration** — 8 category JSON files scraped from Amazon.de, cleaned, and combined into `all_products.json`
- [x] **Input/output guardrails** — scope check, toxicity, duplicate detection, affiliate URL allowlist, price sanity

### Catalog Stats

| Category     | Count | Source |
|-------------|-------|--------|
| CPU         | 20    | Scraped (Amazon.de) |
| GPU         | 44    | Scraped (Amazon.de) |
| Motherboard | 41    | Scraped (Amazon.de) — AM5 + AM4 only, no LGA1851 |
| RAM         | 29    | Scraped (Amazon.de) — desktop DIMM only |
| Storage     | 11    | Scraped (Amazon.de) |
| PSU         | 18    | Scraped (Amazon.de) |
| Case        | 19    | Scraped (Amazon.de) — no mini-ITX |
| Cooling     | 19    | Scraped (Amazon.de) |
| Monitor     | 5     | Manual (hardcoded in seed.py) |
| Keyboard    | 3     | Manual (hardcoded in seed.py) |
| Mouse       | 4     | Manual (hardcoded in seed.py) |
| **Total**   | **213** | |

### Seed Architecture

```
backend/app/db/
├── all_products.json    ← Scraped product catalog (8 categories, ~200 products)
└── seed.py              ← Loads all_products.json + appends peripheral hardcoded data
```

`seed.py` calls `_load_catalog()` which:
1. Reads `all_products.json` (scraped core categories)
2. Appends `_PERIPHERAL_COMPONENTS` (monitors, keyboards, mice — hardcoded until scraped)
3. Returns combined list for `seed_catalog()` to insert into DB

### Known Gaps

- **No LGA1851 motherboards** — Intel Core Ultra CPUs have no matching motherboards in catalog
- **No mini-ITX cases** — scraper didn't return any; mini-ITX builds will have no case options
- **Peripherals not scraped** — monitors, keyboards, mice are still hardcoded with old data
- **Price staleness** — prices are snapshot from scrape date; no automated refresh yet

---

## Remaining Work

### High Priority
- [ ] Scrape peripherals (monitors, keyboards, mice) and add to `all_products.json`
- [ ] Add LGA1851 motherboards for Intel Core Ultra CPU compatibility
- [ ] Add mini-ITX cases
- [ ] Re-seed DB with new catalog data (truncate + re-seed)
- [ ] Test full build flow end-to-end with new catalog

### Medium Priority
- [ ] Write unit tests for `CatalogService`, seed data validation, build integration
- [ ] Set up automated price refresh (scraper on schedule)
- [ ] Add more stores when affiliate approvals come through

### Low Priority
- [ ] Admin UI for catalog management
- [ ] Price history tracking

---

## Architecture

```
User fills form → POST /api/v1/build (BuildRequest)
               → Input guardrails (blocklist, duplicate, budget sanity)
               → Builder service:
                   1. Parse request (goal, budget, preferences)
                   2. CatalogService queries DB → candidate components per category
                      (filtered by: in_stock, brand pref, socket, form_factor, cooling type)
                   3. _format_candidates() builds structured text for Claude
                   4. Claude picks optimal combination (budget + compat + priorities)
               → Output guardrails
               → Persist build → Return BuildResult
```

**Key insight**: Hard constraints (stock, brand, form factor, socket) are filtered by SQL.
Soft optimization (budget allocation, compatibility, value ranking) is Claude's job.

---

## Amazon-Only MVP

Only Amazon.de affiliate links are available right now. The architecture stays multi-store (future-proof), but MVP ships Amazon-only.

### Adding a new store later (checklist)

When ComputerUniverse or Caseking approve affiliate access:
1. Add affiliate link rows to DB (via seed script update or admin tool)
2. Update `stores.yaml` prompt to include the new store
3. Update `search.yaml` with the store's search URL pattern
4. Update `about/page.tsx` affiliate disclosure
5. **No code changes needed** — types, allowlists, and DB schema already support it
