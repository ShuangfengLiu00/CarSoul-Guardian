"""地图能力代理（腾讯地图，经 carModel /map/*）——出行地图页数据源。

前端不直接连 carModel（鉴权域不同），经本 router 转发并注入服务间 JWT。
数据契约与 carModel /map/* 一致：ok/source(live|unavailable)/data 或 error。
"""
from fastapi import APIRouter, Query

from app.services.carsoul_world import _request

router = APIRouter()


@router.get("/status")
async def map_status():
    """地图供应商状态（腾讯默认；key 缺失时 state=unavailable）。"""
    return await _request("GET", "/map/status")


@router.get("/search-poi")
async def map_search_poi(keyword: str = "充电站", region: str | None = None,
                         page_size: int = Query(10, ge=1, le=20)):
    """POI 搜索：充电站 / 门店 / 维修点（腾讯地图）。"""
    params = {"keyword": keyword, "page_size": page_size}
    if region:
        params["region"] = region
    return await _request("GET", "/map/search-poi", params=params)


@router.get("/route")
async def map_route(from_: str = Query(..., alias="from"),
                    to: str = Query(...)):
    """驾车路线规划（腾讯地图）。返回 distance/duration/toll/steps 或诚实降级。"""
    return await _request("GET", "/map/route", params={"from": from_, "to": to})


@router.get("/regeo")
async def map_regeo(location: str = Query(...)):
    """逆地理编码（腾讯地图）：坐标 → 省市区街道。"""
    return await _request("GET", "/map/regeo", params={"location": location})
