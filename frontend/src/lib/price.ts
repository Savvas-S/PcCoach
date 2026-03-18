/**
 * Convert an exact price to a rounded estimated range string (e.g. "€300 – €350").
 * Uses €25 steps below €100 and €50 steps above.
 */
export function priceRange(price: number): string {
  if (!Number.isFinite(price) || price <= 0) return "Check price on store";
  const step = price < 100 ? 25 : 50;
  const low = Math.floor(price / step) * step;
  const high = low + step;
  return `\u20AC${low} \u2013 \u20AC${high}`;
}

/**
 * Convert a total build price to a wider estimated range (€100 steps).
 */
export function totalPriceRange(price: number): string {
  if (!Number.isFinite(price) || price <= 0) return "Check prices on store";
  const step = 100;
  const low = Math.floor(price / step) * step;
  const high = low + step;
  return `\u20AC${low} \u2013 \u20AC${high}`;
}
