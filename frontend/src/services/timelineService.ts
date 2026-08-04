/**
 * Timeline Demo Service — API client for 'A Car's Life' endpoint.
 */
import { get } from "@/utils/request";
import { TIMELINE_DEMO_DATA } from "./timelineData";
import type { LifeStoryResponse } from "./timelineTypes";

export const timelineService = {
  /** Fetch the life story from backend, fall back to demo data on error. */
  lifeStory: async (): Promise<LifeStoryResponse> => {
    try {
      return await get<LifeStoryResponse>("/api/timeline/life-story");
    } catch {
      return TIMELINE_DEMO_DATA;
    }
  },
};
