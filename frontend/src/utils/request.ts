import axios, { AxiosInstance, AxiosRequestConfig } from "axios";
import { message } from "antd";

/**
 * Shared axios instance.
 *
 * In development, Vite proxies `/api` and `/health` to the FastAPI backend
 * (see vite.config.ts), so we use a relative base URL. For production or
 * direct calls, set VITE_API_BASE_URL.
 */
const baseURL = import.meta.env.VITE_API_BASE_URL || "";

export const api: AxiosInstance = axios.create({
  baseURL,
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

// Attach JWT if present (reserved for TASK009 auth wiring).
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("carsoul_token");
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Global error handling.
// 401：令牌可能过期/缺失 → 静默重新登录（utils/silentLogin）后重试一次，
// 避免演示中途（JWT 60 分钟过期）全站突然转 401。
api.interceptors.response.use(
  (resp) => resp,
  async (error) => {
    const status = error?.response?.status;
    if (status === 401 && error.config && !error.config._retry) {
      error.config._retry = true;
      try {
        const { ensureAuthToken } = await import("@/utils/silentLogin");
        const tok = await ensureAuthToken();
        if (tok) {
          error.config.headers = error.config.headers || {};
          error.config.headers.Authorization = `Bearer ${tok}`;
          return api(error.config);
        }
      } catch {
        // 重登失败：落到下面的通用错误提示
      }
    }
    const detail = error?.response?.data?.detail || error?.message || "请求失败";
    if (!axios.isCancel(error)) {
      message.error(typeof detail === "string" ? detail : "请求失败");
    }
    return Promise.reject(error);
  },
);

/** Thin typed HTTP helpers. */
export async function get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const { data } = await api.get<T>(url, config);
  return data;
}

export async function post<T>(url: string, body?: unknown, config?: AxiosRequestConfig): Promise<T> {
  const { data } = await api.post<T>(url, body, config);
  return data;
}

export async function put<T>(url: string, body?: unknown, config?: AxiosRequestConfig): Promise<T> {
  const { data } = await api.put<T>(url, body, config);
  return data;
}

export async function patch<T>(url: string, body?: unknown, config?: AxiosRequestConfig): Promise<T> {
  const { data } = await api.patch<T>(url, body, config);
  return data;
}

export async function del<T = void>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const { data } = await api.delete<T>(url, config);
  return data;
}
