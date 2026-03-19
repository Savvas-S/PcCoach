# PcCoach Frontend — Claude Code Guide

## Architecture Overview

Next.js 15 App Router application with React 19. Dark-themed ("obsidian") UI with gold accents. SSE streaming for real-time build progress. All API calls proxied through Next.js rewrites to the FastAPI backend.

## Directory Structure

```
src/
├── app/
│   ├── layout.tsx                # Root layout: fonts, metadata, AmbientBackground, footer
│   ├── page.tsx                  # Home: hero, "How it works", example builds, trust signals
│   ├── globals.css               # CSS vars, keyframes, utility classes (btn-shimmer, card-glow, etc.)
│   ├── robots.ts                 # Allow /, disallow /api/ and /build/ (ephemeral)
│   ├── sitemap.ts                # /, /build, /find
│   ├── build/
│   │   ├── page.tsx              # Build form: budget → goal → preferences → submit (SSE stream)
│   │   └── [id]/page.tsx         # Build result: components, upgrade/downgrade, warnings
│   ├── find/
│   │   ├── page.tsx              # Component search: category selector → description → result
│   │   └── layout.tsx            # Metadata wrapper (server component)
│   ├── about/page.tsx            # Static: what, how, disclosure, who
│   ├── contact/page.tsx          # Contact info + FAQ (8 questions)
│   ├── privacy/page.tsx          # Privacy policy (9 sections)
│   ├── terms/page.tsx            # Terms of service (12 sections)
│   └── guides/                   # SEO content articles
│       ├── 1000-euro-sweet-spot-build/page.tsx
│       ├── amazon-de-shipping-guide/page.tsx
│       └── cyprus-summer-pc-build/page.tsx
├── components/
│   ├── AmbientBackground.tsx     # Fixed parallax background: aurora gradients + floating orbs
│   ├── BuildLoadingScreen.tsx    # Build progress: component slots, phase labels, progress bar
│   ├── EditorialSection.tsx      # Guide cards grid (server component)
│   ├── ErrorModal.tsx            # Modal overlay with amber accent, ESC/click-outside dismiss
│   └── Toast.tsx                 # Alert banner, auto-dismiss 7s, fixed bottom-center
└── lib/
    ├── api.ts                    # Types, interfaces, API functions (SSE + REST)
    ├── url.ts                    # safeAffiliateUrl(): HTTPS + allowlist validation
    ├── price.ts                  # priceRange(), totalPriceRange(): €-step formatting
    └── budget_goals.json         # Budget→goals mapping (synced from shared/)
```

## Pages & Components

### Client Components ("use client")
- `page.tsx` (home) — hero with staggered fade-up animations, CTA buttons, example builds grid, trust signals
- `build/page.tsx` — form with budget→goal filtering, preferences (4 columns), existing parts checkboxes, SSE streaming
- `build/[id]/page.tsx` — result display with sessionStorage cache, copy-to-clipboard, component cards
- `find/page.tsx` — category selector (12 icons), description textarea, single component result
- `AmbientBackground.tsx` — scroll-driven parallax via refs + requestAnimationFrame throttling
- `BuildLoadingScreen.tsx` — staggered slot reveals (REVEAL_INTERVAL_MS=350), phase progress bar
- `ErrorModal.tsx` — fixed overlay with backdrop blur
- `Toast.tsx` — aria-live="assertive", auto-dismiss

### Server Components
- `layout.tsx` (root) — Google Fonts registration, footer with nav + affiliate disclosure
- `find/layout.tsx` — metadata wrapper
- `EditorialSection.tsx` — 3 guide cards
- All pages under `about/`, `contact/`, `privacy/`, `terms/`, `guides/`

## API Integration (`src/lib/api.ts`)

### Types (mirror backend Pydantic models)
- `UserGoal`, `BudgetRange`, `FormFactor`, `CPUBrand`, `GPUBrand`, `CoolingPreference`, `ComponentCategory`
- `AffiliateSource`: "amazon" | "computeruniverse" | "caseking"
- `BuildRequest`, `BuildResult`, `ComponentRecommendation`, `UpgradeSuggestion`, `DowngradeSuggestion`
- `ComponentSearchRequest`, `ComponentSearchResult`
- `BuildProgress`: phase, turn, elapsed_s, categories_scouted[], categories_queried[], tool
- `BuildPhase`: "scouting" | "selecting" | "validating" | "repairing"

### API Functions

**`submitBuildStream(request, onProgress, signal?)`** → `Promise<BuildResult>`
- POST `/api/v1/build` with SSE streaming
- Uses `ReadableStream` reader + TextDecoder
- Parses SSE frames (double-newline boundaries)
- Handles event types: `progress` → callback, `result` → return, `error` → throw
- Yields to event loop (`setTimeout(r, 0)`) between progress frames for React rendering

**`searchComponent(request, signal?)`** → `Promise<ComponentSearchResult>`
- POST `/api/v1/search`, standard JSON response

**`getBuild(id, signal?)`** → `Promise<BuildResult>`
- GET `/api/v1/build/{id}`, standard JSON response

**`parseError(res, fallback)`** — extracts `detail` from JSON error response

### SOURCE_LABELS
Maps affiliate source keys to display names: `amazon` → "Amazon.de", `computeruniverse` → "ComputerUniverse", `caseking` → "Caseking"

## URL Safety (`src/lib/url.ts`)

```typescript
ALLOWED_AFFILIATE_HOSTS = new Set(["amazon.de", "www.amazon.de"])
```

`safeAffiliateUrl(raw)` → `string | null`
- Rejects: null/undefined, malformed URLs, non-https schemes (javascript:, data:, http:), non-allowlisted hosts
- Must stay in sync with backend `_ALLOWED_AFFILIATE_HOSTS` (models/builder.py + output_guard.py)

## Price Formatting (`src/lib/price.ts`)

- `priceRange(price)` → "€X – €Y" (€25 steps below €100, €50 steps above)
- `totalPriceRange(price)` → "€X – €Y" (€100 steps)
- Fallback: "Check price on store" / "Check prices on store"

## Budget-Goal Mapping (`src/lib/budget_goals.json`)

Synced from `shared/budget_goals.json` via `make sync-config`. Used by the build form to dynamically filter available goals based on selected budget.

```json
{
  "0_1000":    ["low_end_gaming", "light_work"],
  "1000_1500": ["mid_range_gaming", "light_work", "heavy_work", "designer", "architecture"],
  "1500_2000": ["high_end_gaming", "mid_range_gaming", "light_work", "heavy_work", "designer", "architecture"],
  "2000_3000": ["high_end_gaming", "heavy_work", "designer", "architecture"],
  "over_3000": ["high_end_gaming", "heavy_work", "designer", "architecture"]
}
```

## State Management

- **Local `useState`**: all form state (budget, goal, preferences, loading, error, progress)
- **`useSearchParams` + `useEffect`**: auto-populate budget/goal from URL query params (e.g. `/build?budget=1000_1500&goal=mid_range_gaming`)
- **`sessionStorage`**: save BuildResult before navigation → restore on result page (avoids refetch)
- **`useRef`**: scroll parallax in AmbientBackground
- **`useCallback`**: staggered queue drain in BuildLoadingScreen (avoids stale closures)

## Timeouts

| Context | Timeout | Coupled To |
|---------|---------|------------|
| Build form abort | 120,000 ms | Backend `AGENTIC_LOOP_TIMEOUT` (120s) |
| Find form abort | 60,000 ms | — |
| Build result fetch | 30,000 ms | — |

## Design System

### Obsidian Theme (Tailwind)
| Token | Hex | Usage |
|-------|-----|-------|
| `obsidian-bg` | #141414 | Page background |
| `obsidian-surface` | #1C1C1C | Card backgrounds |
| `obsidian-raised` | #242424 | Elevated surfaces |
| `obsidian-border` | #2A2A2A | Borders |
| `obsidian-bright` | #3A3A3A | Bright borders/dividers |
| `obsidian` | #C9A84C | Gold accent (primary) |
| `obsidian-text` | #F5F0E8 | Main text |
| `obsidian-muted` | #8A8070 | Secondary text |
| `obsidian-muted-light` | #5A5045 | Tertiary text |

### Fonts
| Var | Font | Usage |
|-----|------|-------|
| `--font-cormorant` | Cormorant Garamond (300–700, italic) | `font-display` — headings |
| `--font-outfit` | Outfit | `font-body` — body text |
| `--font-jb` | JetBrains Mono | `font-mono` — code/specs |

### Animations
| Name | Duration | Usage |
|------|----------|-------|
| `fade-up` | 0.6s | Page entrance, staggered elements |
| `aurora-1` / `aurora-2` | 40s / 50s | Background aurora gradients |
| `float-1/2/3` | 30s / 36s / 44s | Background floating orbs |
| `pulse-glow` | 5s | CTA button glow |

### CSS Utility Classes (globals.css)
- `.btn-shimmer` — gold sweep shimmer on hover
- `.card-glow` — soft gold glow on hover
- `.build-load-fade-in` — fade-up at 0.8s
- `.build-scan-line` — scanning line (2.4s)
- `.build-slot-check` — pop animation (0.35s)
- `.build-bar-glow` — glowing progress bar

All animations respect `prefers-reduced-motion` (duration set to 0.01ms).

## BuildLoadingScreen Details

- Shows 8 core slots (CPU, Motherboard, GPU, RAM, Storage, PSU, Case, Cooling) + 3 peripheral slots if `include_peripherals`
- Each slot has a custom SVG icon (22x22), fills gold when revealed
- Staggered reveal: queue-driven with `REVEAL_INTERVAL_MS = 350`
- Phase labels: Scouting → Selecting → Validating → Repairing
- Progress bar: percentage based on phase weight + revealed slot count
- Elapsed timer (mm:ss format)
- Accessibility: `role="status"`, `aria-label`, `role="progressbar"` with `aria-valuenow`

## Build Result Page Details

- Tries `sessionStorage` first (cache hit from form submission), else calls `getBuild(id)`
- Components split into core + peripherals sections
- Each `ComponentCard`: category label, name, brand, formatted specs, price range, affiliate link
- `UpgradeCard` (amber): current → upgrade, reason, +cost
- `DowngradeCard` (green): current → downgrade, reason, -savings
- Spec formatting: `SPEC_KEY_OVERRIDES` for TDP, RPM, VRAM, PCIe, DDR display names
- Copy-to-clipboard for shareable build URL

## Configuration

### next.config.js
- `output: "standalone"` — Docker-optimized build
- `proxyTimeout: 120_000` — matches backend agentic loop timeout
- Rewrites: `/api/v1/*` → `${BACKEND_URL}/api/v1/*`
- Security headers: CSP (unsafe-inline for Next.js hydration, unsafe-eval only in dev), X-Frame-Options DENY, Permissions-Policy

### tailwind.config.ts
- Content paths: `src/pages/`, `src/components/`, `src/app/`
- Extended theme: obsidian colors, custom fonts, keyframes, animations
- No plugins

### package.json
- Next.js 15.3.9, React 19.0.0
- Dev: TypeScript 5, ESLint 9, Tailwind 3.4, PostCSS 8.4, Autoprefixer 10.4

## SEO

- `robots.ts`: Allow `/`, disallow `/api/` and `/build/` (ephemeral in-memory builds)
- `sitemap.ts`: `/` (priority 1), `/build` (0.9), `/find` (0.8)
- Each page has custom metadata (title + description)
- Guide pages have publication dates

## Rate Limit Display

- Build form: "2 AI builds per day · no account needed"
- Find form: "2 AI requests per day · no account needed"
- Both share backend `RATE_LIMIT_AI` pool
- Message hidden during loading state

## Dockerfile

Multi-stage build:
1. **deps** — Node 20 Alpine, install dependencies
2. **builder** — Build Next.js with cache mount, `NEXT_TELEMETRY_DISABLED=1`
3. **runner** — Production, non-root user `nextjs:1001`, port 3000, `node server.js`
