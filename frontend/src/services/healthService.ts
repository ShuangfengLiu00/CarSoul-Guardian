import { get } from "@/utils/request";
import type { HealthOverview } from "./types";

export const healthService = {
  overview: () => get<HealthOverview>("/api/health/overview"),
};
