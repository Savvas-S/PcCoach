const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
  include_peripherals?: boolean;
  existing_parts?: ComponentCategory[];
  notes?: string;
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

export async function submitBuild(request: BuildRequest): Promise<BuildResult> {
  const res = await fetch(`${API_URL}/api/v1/build`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!res.ok) throw new Error("Failed to submit build");
  return res.json();
}

export async function getBuild(id: number): Promise<BuildResult> {
  const res = await fetch(`${API_URL}/api/v1/build/${id}`);
  if (!res.ok) throw new Error("Build not found");
  return res.json();
}
