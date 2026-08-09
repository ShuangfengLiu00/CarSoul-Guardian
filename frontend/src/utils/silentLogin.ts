import { useUserStore } from "@/stores/userStore";
import { userService } from "@/services/userService";

// 静默登录（P0 鉴权断链修复，前端侧）：应用启动时用 demo 账号调已豁免的
// /api/user/login 拿真令牌写入 localStorage，使全站 /api 调用带牌。
// 仅 DEV 或显式开启 VITE_SILENT_LOGIN 时生效；生产应改用真实登录页。

const DEMO_USERNAME = import.meta.env.VITE_DEMO_USERNAME || "demo";
const DEMO_PASSWORD = import.meta.env.VITE_DEMO_PASSWORD || "demo1234";
const SILENT_LOGIN = import.meta.env.DEV || import.meta.env.VITE_SILENT_LOGIN === "true";

let inflight: Promise<string | null> | null = null;

/**
 * 确保本地持有有效令牌：已存在则直接返回；否则静默登录/注册 demo 账号后返回。
 * 返回的令牌由 request.ts 的拦截器注入 Authorization，并在 401 时触发重登重试。
 */
export async function ensureAuthToken(): Promise<string | null> {
  const existing = useUserStore.getState().token;
  if (existing) return existing;
  if (!SILENT_LOGIN) return null;
  if (inflight) return inflight;

  inflight = (async () => {
    try {
      let res = await userService
        .login({ username: DEMO_USERNAME, password: DEMO_PASSWORD })
        .catch(() => null);
      if (!res) {
        // 用户不存在则先注册（幂等），再登录
        await userService
          .register({
            username: DEMO_USERNAME,
            password: DEMO_PASSWORD,
            email: `${DEMO_USERNAME}@carsoul.local`,
          })
          .catch(() => null);
        res = await userService
          .login({ username: DEMO_USERNAME, password: DEMO_PASSWORD })
          .catch(() => null);
      }
      if (res?.access_token) {
        useUserStore.getState().login(DEMO_USERNAME, res.access_token);
        return res.access_token;
      }
    } catch {
      // 保持 null，页面走诚实降级
    } finally {
      inflight = null;
    }
    return null;
  })();
  return inflight;
}
