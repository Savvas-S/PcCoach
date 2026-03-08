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
  | "mouse";

export interface BuildRequest {
  goal: UserGoal;
  budget_range: BudgetRange;
  form_factor?: FormFactor;
  cpu_brand?: CPUBrand;
  gpu_brand?: GPUBrand;
  cooling_preference?: CoolingPreference;
  include_peripherals?: boolean;
  existing_parts?: ComponentCategory[];
}

export interface ComponentRecommendation {
  category: ComponentCategory;
  name: string;
  brand: string;
  price_eur: number;
  specs: Record<string, string>;
  affiliate_url?: string;
  affiliate_source?: string;
}

export interface BuildResult {
  id: number;
  components: ComponentRecommendation[];
  total_price_eur?: number;
  summary?: string;
  status: "pending" | "completed" | "failed";
}

async function parseError(res: Response, fallback: string): Promise<string> {
  try {
    const body = await res.json();
    return body?.detail ?? fallback;
  } catch {
    return fallback;
  }
}

export async function submitBuild(
  request: BuildRequest,
  signal?: AbortSignal
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
  return res.json();
}

export async function getBuild(
  id: number,
  signal?: AbortSignal
): Promise<BuildResult> {
  const res = await fetch(`/api/v1/build/${id}`, { signal });
  if (!res.ok) {
    const msg = await parseError(res, "Build not found");
    throw new Error(msg);
  }
  return res.json();
}
