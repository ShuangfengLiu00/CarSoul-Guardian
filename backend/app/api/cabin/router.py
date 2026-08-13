"""座舱陪伴代理（经 carModel /cabin/suggestions|preferences）——座舱页数据源。"""
from fastapi import APIRouter, Query

from app.services.carsoul_world import _request

router = APIRouter()


@router.get("/suggestions")
async def suggestions(vehicle_id: str = Query(...),
                      time_of_day: str | None = None,
                      speed_kmh: float | None = None,
                      occupancy: int = 1):
    """基于场景生成建议卡片（附 control_redline，不下发控制指令）。"""
    params = {"vehicle_id": vehicle_id, "occupancy": occupancy}
    if time_of_day:
        params["time_of_day"] = time_of_day
    if speed_kmh is not None:
        params["speed_kmh"] = speed_kmh
    return await _request("GET", "/cabin/suggestions", params=params)


@router.get("/preferences")
async def preferences_get(vehicle_id: str = Query(...)):
    """读取长期偏好记忆。"""
    return await _request("GET", "/cabin/preferences", params={"vehicle_id": vehicle_id})


@router.post("/preferences")
async def preferences_set(payload: dict):
    """写入长期偏好记忆。"""
    return await _request("POST", "/cabin/preferences", json=payload)
