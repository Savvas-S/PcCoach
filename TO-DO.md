# PcCoach — Affiliate Readiness To-Do

Priority order. Complete each part before moving to the next.

---

## Part 1 — Compliance Fixes (do first, blocks everything else)

### 1.1 Fix the fake phone number
- File: `frontend/src/app/contact/page.tsx`
- Either replace `+357 25 000 000` with a real working number, or delete the entire phone card block
- A fake number that rings nowhere is worse than no number at all

### 1.2 Add per-page affiliate disclosure on result pages
- Files: `frontend/src/app/build/[id]/page.tsx` and `frontend/src/app/find/page.tsx`
- Add a small notice directly above the first store/buy button on each page
- Text: `"Some links on this page are affiliate links. We may earn a small commission at no extra cost to you."`
- Style it as a subtle gray note, not a banner — it should inform without dominating

### 1.3 Update footer disclosure to cover all stores
- File: `frontend/src/app/layout.tsx`
- Current text only mentions Amazon Associates
- Replace with: `"As an Amazon Associate and affiliate of selected EU retailers, we earn from qualifying purchases at no extra cost to you."`

---

## Part 2 — Technical SEO Basics

### 2.1 Add sitemap.xml
- Create `frontend/src/app/sitemap.ts`
- Include: `/`, `/build`, `/find`, `/about`, `/contact`, `/privacy`, `/terms`
- Next.js 15 has built-in sitemap support — return a `MetadataRoute.Sitemap` array
- Reference: https://nextjs.org/docs/app/api-reference/file-conventions/metadata/sitemap

### 2.2 Add robots.txt
- Create `frontend/src/app/robots.ts`
- Allow all crawlers, point to sitemap
- Reference: https://nextjs.org/docs/app/api-reference/file-conventions/metadata/robots

### 2.3 Add OG meta tags to static pages
- Files: `frontend/src/app/about/page.tsx`, `frontend/src/app/contact/page.tsx`, `frontend/src/app/privacy/page.tsx`, `frontend/src/app/terms/page.tsx`
- Add `openGraph` block to each page's `metadata` export
- Minimum fields: `title`, `description`, `url`, `siteName: "PcCoach"`, `type: "website"`

### 2.4 Add OG meta tags to build result pages
- File: `frontend/src/app/build/[id]/page.tsx`
- This is a dynamic client component — generate the title in the `<head>` using `useEffect` + `document.title`, or convert the wrapper to a server component that fetches the build and exports metadata
- Minimum: dynamic title like `"PC Build — PcCoach"` and a description

### 2.5 Add a favicon
- Add `frontend/public/favicon.ico` (and optionally `favicon.svg`, `apple-touch-icon.png`)
- Current `/public` directory is empty — the site shows the browser default icon

---

## Part 3 — Content: Examples Page

### 3.1 Create `/examples` page
- Create `frontend/src/app/examples/page.tsx`
- Show 4–5 static pre-written build examples at different price points:
  - Budget Gaming (~€700)
  - Mid-Range Gaming (~€1,200)
  - High-End Gaming (~€2,000)
  - Work / Productivity (~€1,000)
  - Content Creator / Video Editing (~€1,800)
- Each example should look identical to a real `/build/[id]` result:
  - Component list with category badges, specs, prices
  - "Buy →" buttons pointing to real store search URLs
  - A short summary paragraph
- This page proves the tool works without requiring the user to generate anything
- Add it to the homepage feature section and footer nav
- Add affiliate disclosure note on this page (same as Part 1.2)

### 3.2 Add homepage preview
- File: `frontend/src/app/page.tsx`
- Below the feature cards, add a "See an example build" section
- Show a condensed 3–4 component snippet (CPU, GPU, RAM, Storage) from a sample build
- Include a "See full example →" link to `/examples`
- This gives new visitors proof of quality before they commit to filling the form

---

## Part 4 — Content: Articles / Guides

Create a `/guides` section. These articles serve two purposes: give Amazon Associates reviewers evidence of content, and bring in organic search traffic.

### 4.1 Create guides index page
- Create `frontend/src/app/guides/page.tsx`
- Lists all articles with title, short description, and a link to each
- Add link to guides in the footer nav

### 4.2 Write article 1 — Beginner guide
- Route: `/guides/how-to-build-a-pc`
- Title: `"How to Build a PC: A Beginner's Guide for 2026"`
- Content: explain the components (CPU, GPU, RAM etc.), why each matters, what to buy first
- 600–900 words
- Link to the build tool naturally at the end: `"Not sure where to start? Use our free PC builder to get a full component list instantly."`

### 4.3 Write article 2 — Budget guide
- Route: `/guides/pc-build-budget-guide`
- Title: `"How Much Should You Spend on Each PC Component?"`
- Content: break down the budget allocation logic (GPU ~35%, CPU ~15% etc.), explain trade-offs
- 500–700 words
- Link naturally to the build tool and examples page

### 4.4 Write article 3 — Build vs buy
- Route: `/guides/build-vs-buy-pc`
- Title: `"Building a PC vs Buying Pre-Built: What's Worth It in 2026?"`
- Content: honest comparison, when building makes sense, why for Cyprus/EU market building is often better value
- 500–700 words
- Link to build tool at end

### 4.5 Article page template
- All articles should share the same layout: back link, title, last-updated date, body text, CTA to build tool at the bottom
- Keep styling consistent with the rest of the site (gray-900 background, white text)

---

## Part 5 — Trust Signals

### 5.1 Add a "builds generated" counter to the homepage
- File: `frontend/src/app/page.tsx`
- Add a simple stat line near the CTA: e.g. `"500+ builds generated"` or `"Trusted by PC builders in Cyprus and across Europe"`
- Track count in the backend in-memory store (already exists) and expose it via a lightweight `GET /api/v1/stats` endpoint that returns `{ builds_generated: N }`
- If the number is low, use a static floor: show `"100+"` until real numbers exceed it

### 5.2 Add social links (optional but useful)
- File: `frontend/src/app/layout.tsx` (footer)
- Even a Twitter/X link with a basic account helps — it signals the project is real and maintained
- Do not add if you have no presence — a dead social link is worse than none

---

## Part 6 — Affiliate Programme Applications

Do this only after Parts 1–3 are complete.

### 6.1 Awin (already pending)
- Wait for network-level approval
- Once approved, apply individually to:
  - **computeruniverse.net** (Awin merchant)
  - **Caseking.de** (Awin merchant)
- Update `backend/app/prompts/sections/stores.yaml` and `backend/app/services/claude.py` with real affiliate URL patterns once merchant IDs are issued

### 6.2 Amazon Associates (amazon.de)
- Apply after: Part 1 compliance fixes, Part 3 examples page, Part 4 at least 2 articles
- Use the amazon.de Associates programme (not .com) — correct for the EU market
- Affiliate tag `thepccoach-21` is already wired into the codebase
- Verify the tag is correct in your Amazon Associates account before going live

### 6.3 Mindfactory.de (future — after traffic)
- Major German PC hardware retailer
- Apply via Belboon affiliate network or check for a direct programme
- Good fallback for components not well-covered by computeruniverse/caseking

### 6.4 ALTERNATE.de (future — after traffic)
- Another large German PC parts retailer
- Available via Awin — apply as a second merchant after the first two are approved

---

## Part 7 — Before Going Public

These are not required for affiliate applications but should be done before driving real traffic.

### 7.1 Replace in-memory store with database
- See memory: DB + request hash caching is pending
- Without a DB, builds are lost on every container restart
- Shareable build links currently break after a redeploy

### 7.2 Add rate limiting review
- Rate limiting is in place (10/hour on /build, 20/hour on /search)
- Before public launch, evaluate if these limits are correct for expected traffic patterns

### 7.3 Add a real email inbox for support@pccoach.io
- Verify this address actually receives email
- An affiliate network or user trying to reach you and getting a bounce is a trust failure

---

## Quick Reference — File Locations

| What | File |
|------|------|
| Footer disclosure | `frontend/src/app/layout.tsx` |
| Build result page | `frontend/src/app/build/[id]/page.tsx` |
| Find result page | `frontend/src/app/find/page.tsx` |
| Contact page | `frontend/src/app/contact/page.tsx` |
| Homepage | `frontend/src/app/page.tsx` |
| Store URL formats | `backend/app/prompts/sections/stores.yaml` |
| Affiliate tag (Amazon) | `backend/app/prompts/sections/stores.yaml` |
| Claude service | `backend/app/services/claude.py` |
