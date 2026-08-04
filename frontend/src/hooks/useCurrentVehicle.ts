import { useCallback, useEffect, useState } from "react";
import { vehicleService } from "@/services";
import type { Vehicle } from "@/services/types";

/**
 * 车机大屏模式：全站唯一的"本车"数据源。
 *
 * 系统部署在汽车大屏上时，屏幕只服务于本车，不存在多车切换概念。
 * 此 Hook 自动锁定第一辆车作为本车（后端仍可保留多车能力用于演示/seed），
 * 所有页面统一消费此 Hook，不再各自维护车辆选择器。
 *
 * - 自动拉取，无需传参
 * - loading: 首次加载中
 * - vehicle: 本车（无车时为 null）
 * - hasNoVehicle: 是否完全无车（用于引导生成模拟数据）
 * - refresh: 重新拉取
 */
export function useCurrentVehicle() {
  const [vehicle, setVehicle] = useState<Vehicle | null>(null);
  const [loading, setLoading] = useState(true);
  const [hasNoVehicle, setHasNoVehicle] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await vehicleService.list();
      if (data.items.length > 0) {
        setVehicle(data.items[0]);
        setHasNoVehicle(false);
      } else {
        setVehicle(null);
        setHasNoVehicle(true);
      }
    } catch {
      setVehicle(null);
      setHasNoVehicle(false); // 接口异常不判定为"无车"，避免误导
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { vehicle, loading, hasNoVehicle, refresh };
}
