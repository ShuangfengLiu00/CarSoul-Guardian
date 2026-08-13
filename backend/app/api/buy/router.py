"""购车顾问代理（经 carModel /vehicle/catalog|recommend|compare）——购车页数据源。"""
from fastapi import APIRouter, Query

from app.services.carsoul_world import _request

router = APIRouter()


@router.get("/catalog")
async def catalog():
    """车型库列表（10 款真实在售 EV，含续航/保值评分）。"""
    return await _request("GET", "/vehicle/catalog")


@router.post("/recommend")
async def recommend(payload: dict):
    """按预算/偏好化学/用途推荐（评分排序，演示口径）。"""
    return await _request("POST", "/vehicle/recommend", json=payload)


@router.get("/compare")
async def compare(a: str = Query(..., description="车型名，如 'Tesla Model Y'"),
                  b: str = Query(..., description="车型名，如 'BYD Seal'")):
    """两款车型配置对比。"""
    return await _request("GET", "/vehicle/compare", params={"a": a, "b": b})
