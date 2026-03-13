# PcCoach Backend — Security Audit

## Dependency Vulnerability Scan

**Tool:** `pip-audit` (via `uv run pip-audit`)
**Date:** 2026-03-13
**Command:** `pip-audit`

### Results

```
No known vulnerabilities found
Name            Skip Reason
--------------- -----------------------------------------------------------------------
pccoach-backend Dependency not found on PyPI and could not be audited: pccoach-backend
```

**Verdict:** ✅ No HIGH or CRITICAL CVEs found in any direct or transitive dependency.

The `pccoach-backend` package itself is skipped because it is a local package not
published to PyPI — this is expected and not a concern.

---

## How to Re-run

```bash
# Inside the backend container or local venv:
uv run pip-audit

# For a full JSON report:
uv run pip-audit --format json -o audit-report.json
```

Re-run after every `uv lock` / dependency update.  Consider adding to CI.

---

## Manual Review Items

| # | Area | Status | Notes |
|---|------|--------|-------|
| 1 | `anthropic` SDK | ✅ Pinned via uv.lock | Review after each SDK release |
| 2 | `fastapi` / `starlette` | ✅ No CVEs | Pin minor version in prod |
| 3 | `pydantic` v2 | ✅ No CVEs | |
| 4 | `cachetools` | ✅ No CVEs | In-memory only; replace with Redis in prod |
| 5 | `slowapi` | ✅ No CVEs | |

---

## Recommended CI Integration

```yaml
# .github/workflows/security.yml (example)
- name: Dependency audit
  run: cd backend && pip-audit --strict
```

`--strict` causes a non-zero exit on any vulnerability, breaking the build.
