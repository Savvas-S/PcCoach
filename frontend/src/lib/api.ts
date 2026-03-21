export type UserGoal =
  | "high_end_gaming"
  | "mid_range_gaming"
  | "low_end_gaming"
  | "light_work"
  | "heavy_work"
  | "designer"
  | "architecture";

export type BudgetRange =
  | "0_1000"
  | "1000_1500"
  | "1500_2000"
  | "2000_3000"
  | "over_3000";

export type FormFactor = "atx" | "micro_atx" | "mini_itx";
export type CPUBrand = "intel" | "amd" | "no_preference";
export type GPUBrand = "nvidia" | "amd" | "no_preference";
export type CoolingPreference = "no_preference" | "liquid" | "air";
export type ComponentCategory =
  | "cpu"
  | "gpu"
  | "motherboard"
  | "ram"
  | "storage"
  | "psu"
  | "case"
  | "cooling"
  | "monitor"
  | "keyboard"
  | "mouse"
  | "toolkit";

export interface BuildRequest {
  goal: UserGoal;
  budget_range: BudgetRange;
  form_factor?: FormFactor;
  cpu_brand?: CPUBrand;
  gpu_brand?: GPUBrand;
  cooling_preference?: CoolingPreference;
  include_peripherals?: boolean;
  existing_parts?: ComponentCategory[];
  notes?: string;
}

export type AffiliateSource = "amazon" | "computeruniverse" | "caseking";

export const SOURCE_LABELS: Record<AffiliateSource, string> = {
  amazon: "Amazon.de",
  computeruniverse: "ComputerUniverse",
  caseking: "Caseking",
};

export interface ComponentRecommendation {
  category: ComponentCategory;
  name: string;
  brand: string;
  price_eur: number;
  specs: Record<string, string>;
  affiliate_url?: string;
  affiliate_source?: AffiliateSource;
}

export interface DowngradeSuggestion {
  component_category: ComponentCategory;
  current_name: string;
  downgrade_name: string;
  savings_eur: number;
  reason: string;
  affiliate_url?: string;
  affiliate_source?: AffiliateSource;
}

export interface UpgradeSuggestion {
  component_category: ComponentCategory;
  current_name: string;
  upgrade_name: string;
  extra_cost_eur: number;
  reason: string;
  affiliate_url?: string;
  affiliate_source?: AffiliateSource;
}

export interface BuildResult {
  id: string;
  components: ComponentRecommendation[];
  total_price_eur?: number;
  summary?: string;
  upgrade_suggestion?: UpgradeSuggestion;
  downgrade_suggestion?: DowngradeSuggestion;
  status: "completed";
  warnings?: string[];
}

export interface ComponentSearchRequest {
  category: ComponentCategory;
  description: string;
}

export interface ComponentSearchResult {
  name: string;
  brand: string;
  category: ComponentCategory;
  estimated_price_eur: number;
  reason: string;
  specs: Record<string, string>;
  affiliate_url: string | null;
  affiliate_source: AffiliateSource | null;
}

async function parseError(res: Response, fallback: string): Promise<string> {
  try {
    const body = await res.json();
    return body?.detail ?? fallback;
  } catch {
    return fallback;
  }
}

export type BuildPhase = "scouting" | "selecting" | "validating" | "repairing" | "summarizing";

export interface BuildProgress {
  phase: BuildPhase;
  turn: number;
  elapsed_s: number;
  categories_scouted: string[];
  categories_queried: string[];
  tool: string;
}

export async function submitBuildStream(
  request: BuildRequest,
  onProgress: (progress: BuildProgress) => void,
  signal?: AbortSignal,
): Promise<BuildResult> {
  const res = await fetch(`/api/v1/build`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal,
  });
  if (!res.ok) {
    const msg = await parseError(res, "Failed to submit build");
    throw new Error(msg);
  }

  if (!res.body) throw new Error("Server returned an empty response");
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result: BuildResult | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // Parse complete SSE frames (separated by double newlines)
    let boundary: number;
    while ((boundary = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);

      let eventType = "";
      let data = "";
      for (const line of frame.split("\n")) {
        if (line.startsWith("event: ")) eventType = line.slice(7);
        else if (line.startsWith("data: ")) data = line.slice(6);
      }

      if (!eventType || !data) continue;

      if (eventType === "progress") {
        try { onProgress(JSON.parse(data)); } catch { /* skip malformed */ }
        // Yield to the event loop so React can render the progress update
        // before we process the next frame in the same chunk.
        await new Promise((r) => setTimeout(r, 0));
      } else if (eventType === "result") {
        try {
          const parsed = JSON.parse(data);
          if (!parsed || !parsed.id || !Array.isArray(parsed.components)) {
            throw new Error("Malformed build result from server");
          }
          result = parsed;
        } catch {
          throw new Error("Received an invalid build result. Please try again.");
        }
      } else if (eventType === "error") {
        let detail = "Build generation failed";
        try { detail = JSON.parse(data).detail || detail; } catch { /* use default */ }
        throw new Error(detail);
      }
    }
  }

  if (!result) throw new Error("Stream ended without a result");
  return result;
}

export async function searchComponent(
  request: ComponentSearchRequest,
  signal?: AbortSignal
): Promise<ComponentSearchResult> {
  const res = await fetch(`/api/v1/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal,
  });
  if (!res.ok) {
    const msg = await parseError(res, "Failed to find component");
    throw new Error(msg);
  }
  return res.json();
}

export async function getBuild(
  id: string,
  signal?: AbortSignal
): Promise<BuildResult> {
  const res = await fetch(`/api/v1/build/${id}`, { signal });
  if (!res.ok) {
    const msg = await parseError(res, "Build not found");
    throw new Error(msg);
  }
  return res.json();
}
