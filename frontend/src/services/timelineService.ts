/**
 * Timeline Demo Service — API client for 'A Car's Life' endpoint.
 *
 * 红线2（BC-20）：后端失败时**不得**静默回落到剧本数据。
 * 异常一律向上抛出，由页面渲染显式错误态。
 */
import { get } from "@/utils/request";
import type { LifeStoryResponse } from "./timelineTypes";

export const timelineService = {
  /**
   * Fetch the life story from backend.
   * @throws 后端不可用 / 非 2xx 时向上抛出，调用方必须处理错误态。
   */
  lifeStory: async (): Promise<LifeStoryResponse> => {
    return await get<LifeStoryResponse>("/api/timeline/life-story");
  },
};
