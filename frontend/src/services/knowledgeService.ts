import { get, post } from "@/utils/request";
import type {
  KnowledgeSearchRequest,
  KnowledgeSearchResponse,
  KnowledgeIngestRequest,
  KnowledgeIngestResponse,
  KnowledgeStats,
} from "./types";

export const knowledgeService = {
  search: (body: KnowledgeSearchRequest) =>
    post<KnowledgeSearchResponse>("/api/knowledge/search", body),

  ingest: (body: KnowledgeIngestRequest) =>
    post<KnowledgeIngestResponse>("/api/knowledge/ingest", body),

  stats: () => get<KnowledgeStats>("/api/knowledge/stats"),

  rebuild: () =>
    post<{ chunks: number; message: string; stats: KnowledgeStats }>(
      "/api/knowledge/rebuild",
    ),
};
