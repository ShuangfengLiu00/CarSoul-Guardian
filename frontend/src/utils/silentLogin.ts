import { useUserStore } from "@/stores/userStore";
import { userService } from "@/services/userService";

// 静默登录（P0 鉴权断链修复，前端侧）：应用启动时用 demo 账号调已豁免的
// /api/user/login 拿真令牌写入 localStorage，使全站 /api 调用带牌。
//
// 默认开启（包括生产构建）：本项目当前以 demo 形态对外展示，没有真实登录页，
// 若生产构建默认关闭会导致 Vite 把整段死代码消除 → 首次访问 /api 全 401 + 静默登录
// 失败时还会把"无车"和"鉴权失败"误当成同一件事（useCurrentVehicle 兜底把 vehicle
// 置 null，主区域显示「暂无车辆」，而顶部冒出 Unauthorized 红条）。
//
// 仅当显式 VITE_SILENT_LOGIN=false 时禁用（留出未来接真登录页的开关）。
const DEMO_USERNAME = import.meta.env.VITE_DEMO_USERNAME || "demo";
const DEMO_PASSWORD = import.meta.env.VITE_DEMO_PASSWORD || "demo1234";
const SILENT_LOGIN = import.meta.env.VITE_SILENT_LOGIN !== "false";

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
