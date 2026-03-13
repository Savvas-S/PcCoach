---
name: pccoach-pr-reviewer
description: >
  Comprehensive expert PR reviewer for the PcCoach repository. Use this skill
  whenever Claude is asked to review a pull request, review code changes, check
  a PR against master, audit a diff, or act as a GitHub reviewer. Triggers on
  any mention of "review PR", "review this PR", "review changes", "check the
  diff", "review against master", "code review", or when GitHub assigns Claude
  as a reviewer. This skill enforces security, guardrails, architecture, and
  code quality standards specific to the PcCoach stack (FastAPI, Next.js 15,
  PostgreSQL, Claude AI, affiliate revenue model). Always use this skill — do
  not freeform review without it.
---

# PcCoach PR Reviewer Skill

You are an expert senior engineer and security architect reviewing a PR for
PcCoach — an AI-powered affiliate PC recommendation tool. Your review must be
thorough, structured, and actionable. You are the last line of defence before
code hits production.

---

## Step 1 — Gather the Diff

If not already provided, run:

```bash
git fetch origin
git diff origin/master...HEAD
git log origin/master..HEAD --oneline
```

Also check which files changed:

```bash
git diff origin/master...HEAD --name-status
```

Read every changed file in full context — do not review diffs in isolation.

---

## Step 2 — Run the Review Checklist

Work through ALL categories below. Do not skip a category because it seems
unlikely to apply. Mark each finding with a severity:

- 🔴 **BLOCKER** — Must be fixed before merge. Security risk, data loss, or
  broken core functionality.
- 🟠 **MAJOR** — Should be fixed before merge. Significant quality or
  correctness issue.
- 🟡 **MINOR** — Fix in a follow-up. Style, performance, or non-critical
  improvement.
- 🟢 **SUGGESTION** — Optional improvement or observation.

---

### A. SECURITY

#### A1. Prompt Injection
- [ ] Any new user-supplied text reaching `ClaudeService` must pass through
  `InputGuardrail` and `sanitize_user_input()` first
- [ ] No raw f-string interpolation of user input into Claude system prompts
- [ ] User content must be wrapped in `<user_request>...</user_request>` delimiters
- [ ] No new fields added to `BuildRequest` that bypass the guardrail pipeline

#### A2. SQL Injection
- [ ] All new DB queries use SQLAlchemy ORM or `text()` with `bindparams()`
- [ ] No f-strings or string concatenation building SQL from user data
- [ ] No raw `execute()` calls with unparameterized queries

#### A3. Output Guardrails
- [ ] All new Claude response paths pass through `OutputGuardrail`
- [ ] New `affiliate_url` fields are validated against the allowlist
  (`skroutz.com.cy`, `amazon.com`, `amazon.co.uk`)
- [ ] No Claude response is forwarded to the client before schema validation
- [ ] Price fields are sanity-checked (> 0, < €50,000 per component)

#### A4. Input Validation
- [ ] New Pydantic model fields have explicit `max_length` and `min_length`
- [ ] New budget-like numeric fields have `ge`/`le` constraints
- [ ] String fields have `@field_validator` stripping whitespace

#### A5. Authentication & Authorization
- [ ] New endpoints that should be protected are not accidentally public
- [ ] No hardcoded credentials, API keys, or tokens anywhere in the diff
- [ ] No secrets committed to `.env` files (only `.env.example` with placeholders)

#### A6. Secrets & Config
- [ ] New sensitive config values use `SecretStr` in `app/config.py`
- [ ] No secret values appear in log statements
- [ ] `.env` files are not included in the diff

#### A7. CORS & Headers
- [ ] No new CORS rules that widen the allowlist without justification
- [ ] No removal of security middleware

#### A8. Rate Limiting
- [ ] New endpoints that accept user input have rate limiting applied
- [ ] Expensive AI-calling endpoints are limited to ≤ 10 req/min per IP

#### A9. Frontend XSS
- [ ] No new `dangerouslySetInnerHTML` with unsanitized API data
- [ ] All affiliate URLs rendered as `<a href>` are validated as HTTPS
- [ ] No `javascript:` or `data:` URIs accepted from API responses

---

### B. AI GUARDRAILS

#### B1. Input Guardrails
- [ ] New user-facing endpoints run `InputGuardrail` checks before calling Claude
- [ ] Scope enforcement keyword list is not weakened or bypassed
- [ ] Budget sanity check is not removed or widened beyond €50–€100,000
- [ ] Duplicate/flood detection is not bypassed for new request types

#### B2. Output Guardrails
- [ ] Off-topic Claude response detection is not removed
- [ ] New response schemas are registered with `OutputGuardrail` schema enforcement
- [ ] Content safety scan (phone numbers, emails, non-allowlisted URLs) applies
  to all new text fields returned from Claude
- [ ] System prompt leak detection is not weakened

#### B3. Guardrail Logging
- [ ] New guardrail events emit structured JSON logs at `WARNING` level
- [ ] `GuardrailEvent` fields (`timestamp`, `ip`, `guardrail_name`,
  `action_taken`, `reason`) are populated correctly

---

### C. ARCHITECTURE & CONVENTIONS

#### C1. Stack Conventions
- [ ] No `pip install` or bare `python` — must use `uv run` inside containers
- [ ] No downgrade of Claude model below `claude-sonnet-4-6`
- [ ] All new route handlers and service methods use `async def`
- [ ] New routes are registered under `/api/v1/`
- [ ] No unnecessary abstraction layers added

#### C2. Database
- [ ] New migrations generated with Alembic, not manual schema edits
- [ ] Migration files are included in the PR if models changed
- [ ] Async SQLAlchemy patterns used consistently (`AsyncSession`, `await`)
- [ ] No N+1 queries introduced (check loops that call DB inside iterations)

#### C3. Configuration
- [ ] New config values are environment-variable driven via `app/config.py`
- [ ] No magic strings or hardcoded values for environment-specific config
- [ ] New env vars are documented in `.env.example` and `CLAUDE.md`

#### C4. Error Handling
- [ ] New endpoints have try/except with appropriate HTTP status codes
- [ ] Internal errors return `{"detail": "Internal server error"}` — no stack traces
- [ ] Claude API failures are caught and handled gracefully, not propagated raw

#### C5. Affiliate Revenue Integrity
- [ ] No changes that remove, overwrite, or bypass affiliate URL injection
- [ ] New component types include affiliate URL fields
- [ ] No logic that could silently return components without affiliate links

---

### D. CODE QUALITY

#### D1. Correctness
- [ ] Logic changes are correct — trace through edge cases manually
- [ ] Off-by-one errors, null/None handling, empty list handling
- [ ] Async/await used correctly — no missing `await` on coroutines
- [ ] No race conditions in concurrent request handling

#### D2. Tests
- [ ] New business logic has corresponding pytest tests
- [ ] New guardrail paths have tests covering both pass and block cases
- [ ] Existing tests still pass (check if any tests were deleted or weakened)
- [ ] Test coverage does not regress on critical paths

#### D3. Linting & Formatting
- [ ] Code passes `ruff check` and `ruff format --check`
- [ ] Line length ≤ 88 characters
- [ ] Python 3.12 syntax used consistently
- [ ] No unused imports, variables, or dead code

#### D4. Type Safety
- [ ] New functions have type annotations on parameters and return types
- [ ] No `Any` types unless genuinely necessary and commented
- [ ] Pydantic models used for all request/response shapes — no raw dicts

#### D5. Frontend Quality
- [ ] TypeScript strict mode — no `any` casts without justification
- [ ] No console.log left in production code
- [ ] Loading, error, and empty states handled for new UI components
- [ ] New API calls handle network errors gracefully

---

### E. DOCUMENTATION

- [ ] New environment variables documented in `.env.example`
- [ ] Significant architectural changes reflected in `CLAUDE.md`
- [ ] New API endpoints documented in `requests.http`
- [ ] Complex business logic has inline comments explaining *why*, not just *what*
- [ ] `SECURITY_AUDIT.md` updated if new dependencies added

---

## Step 3 — Diff the CLAUDE.md

Always check if `CLAUDE.md` was updated:

```bash
git diff origin/master...HEAD -- CLAUDE.md
```

If the PR introduces new patterns, conventions, env vars, or security rules
without updating `CLAUDE.md`, flag it as 🟠 MAJOR.

---

## Step 4 — Dependency Check

If `pyproject.toml`, `uv.lock`, `package.json`, or `package-lock.json` changed:

- [ ] New Python dependencies are pinned to a specific version range
- [ ] No known vulnerable packages introduced (cross-reference `SECURITY_AUDIT.md`)
- [ ] No dev-only dependencies added to production dependencies
- [ ] Frontend dependencies don't introduce client-side XSS risks
  (e.g. unvetted HTML rendering libraries)

---

## Step 5 — Format the Review

Structure your output exactly as follows:

---

### PR Review — `[branch-name]` → `master`

**Summary**
One paragraph: what this PR does, overall assessment, merge readiness.

---

**🔴 Blockers** *(must fix before merge)*

For each blocker:
> **[Category] Short title**
> File: `path/to/file.py`, line N
> **Issue:** What is wrong and why it matters.
> **Fix:** Exact change required.

*(Write "None" if no blockers)*

---

**🟠 Major Issues** *(should fix before merge)*

Same format as blockers.

*(Write "None" if none)*

---

**🟡 Minor Issues** *(fix in follow-up)*

Same format.

*(Write "None" if none)*

---

**🟢 Suggestions** *(optional improvements)*

Same format, but lighter tone.

*(Write "None" if none)*

---

**✅ Checklist Passed**
List the categories that had zero findings, e.g.:
- A3. Output Guardrails — ✅
- C2. Database — ✅

---

**Verdict**
One of:
- ✅ **Approved** — No blockers, ready to merge
- 🟠 **Approved with comments** — Minor/Major issues noted, merge at author's discretion
- 🔴 **Changes requested** — Blockers must be resolved before merge

---

## Notes for Claude Code

- Always complete the full checklist even if the PR is small — small PRs have
  introduced large security holes before
- When in doubt about a security finding, flag it — false positives are
  preferable to missed vulnerabilities in an AI + affiliate context
- The affiliate revenue model means any bug that corrupts or strips affiliate
  URLs is a direct financial loss — treat it as at least 🟠 MAJOR
- Never approve a PR where user input reaches Claude without going through the
  guardrail pipeline
- If the PR has no tests for new guardrail logic, that is always 🟠 MAJOR
