/** True when a price is a usable positive number. */
export function isValidPrice(price: number): boolean {
  return Number.isFinite(price) && price > 0;
}

/**
 * Format a price as a clean euro string (e.g. "€299.00").
 * Returns "Check price on store" for invalid/zero prices.
 */
export function formatPrice(price: number): string {
  if (!isValidPrice(price)) return "Check price on store";
  return `\u20AC${price.toFixed(2)}`;
}

/**
 * Format a total build price (e.g. "€1,249.00").
 * Returns "Check prices on store" for invalid/zero prices.
 */
export function formatTotalPrice(price: number): string {
  if (!Number.isFinite(price) || price <= 0) return "Check prices on store";
  return `\u20AC${price.toLocaleString("en-IE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
