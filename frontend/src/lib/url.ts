/**
 * Affiliate URL safety utilities.
 *
 * Validates that a URL is:
 *  - An https:// URL (not javascript:, data:, http:, etc.)
 *  - Points to an allowlisted affiliate domain
 *
 * Use `safeAffiliateUrl()` on every URL before rendering it as <a href=...>.
 */

const ALLOWED_AFFILIATE_HOSTS = new Set([
  "amazon.de",
  "www.amazon.de",
  "computeruniverse.net",
  "www.computeruniverse.net",
  "caseking.de",
  "www.caseking.de",
]);

/**
 * Returns the URL string if it is safe to render, or null if it should be
 * suppressed (blocked scheme, non-allowlisted host, or malformed URL).
 */
export function safeAffiliateUrl(raw: string | undefined | null): string | null {
  if (!raw) return null;

  let url: URL;
  try {
    url = new URL(raw);
  } catch {
    return null; // malformed
  }

  // Block dangerous schemes
  if (url.protocol !== "https:") return null;

  // Require allowlisted host
  if (!ALLOWED_AFFILIATE_HOSTS.has(url.hostname)) return null;

  return url.href;
}
