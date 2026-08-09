"""SQLite 外键级联删除真实集成测试（P0 修复 2026-08-09）。

背景：`app/database/connection.py` 给 SQLite 引擎挂了 `connect` 事件，在每次
连接建立时执行 `PRAGMA foreign_keys=ON`，让 models 里 `ondelete="CASCADE"`
真正生效。`VehicleHealthSnapshot.vehicle_id` 等即声明了
`ForeignKey("vehicles.id", ondelete="CASCADE")`。

为什么必须测"级联真发生"而不是"PRAGMA 返回 1"：
- 只断言 PRAGMA 拨到 ON，证明的是"开关拨了"，不证明级联删除发生；
- 真正的风险是：用户行使「删除我的数据」权利（删车）后，关联健康快照 /
  故障日志 / 行为数据变成孤儿行留在库里——这是 PIPL 删除权的实质性不达标。
所以这里走完整业务语义：建车 → 建关联快照 → 删车 → 断言关联数据为 0。

监听器函数 `_enable_sqlite_foreign_keys` 直接从生产模块导入，确保测的是
**同一份生产代码**，而不是另写一份副本。
"""

from __future__ import annotations

import os
import tempfile

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.database.connection import _enable_sqlite_foreign_keys
from app.models import Vehicle, VehicleHealthSnapshot


def _make_engine(enable_fk: bool):
    """建一个临时文件 SQLite 引擎。

    enable_fk=True 时挂上生产同款 `_enable_sqlite_foreign_keys` 监听器；
    False 时不挂（对照组，模拟修复前的行为）。两张表结构与生产完全一致。
    """
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    eng = create_engine(
        f"sqlite:///{path}", connect_args={"check_same_thread": False}
    )
    if enable_fk:
        event.listen(eng, "connect", _enable_sqlite_foreign_keys)
    Base.metadata.create_all(eng)
    return eng, path


def _seed_and_delete(eng):
    """建一辆车 + 一条关联健康快照，删车，返回 (删除前快照数, 删除后快照数)。"""
    SessionLocal = sessionmaker(bind=eng)
    db = SessionLocal()
    try:
        v = Vehicle(brand="BYD", model="Han", year=2024, vin="LGXCAFE0001TEST")
        db.add(v)
        db.flush()  # 拿到 v.id 才能挂关联快照
        snap = VehicleHealthSnapshot(vehicle_id=v.id, health_score=88, mileage=12000)
        db.add(snap)
        db.commit()
        before = db.query(VehicleHealthSnapshot).count()
        db.delete(v)
        db.commit()
        after = db.query(VehicleHealthSnapshot).count()
        return before, after
    finally:
        db.close()


def test_sqlite_foreign_keys_on_cascades_children():
    """PRAGMA foreign_keys=ON（修复后）：删车后关联快照应为 0（PIPL 删除权）。"""
    eng, path = _make_engine(enable_fk=True)
    try:
        before, after = _seed_and_delete(eng)
        assert before == 1, "前置：应恰好插入 1 条关联快照"
        assert after == 0, "删车后关联快照应被级联清除，而非留作孤儿行"
    finally:
        eng.dispose()
        os.remove(path)


def test_sqlite_foreign_keys_off_leaves_orphans():
    """对照组（修复前行为）：外键关闭时删车，关联快照残留成孤儿行。

    本用例记录的是**修复前会被观察到的错误行为**，断言其确实发生，用以证明
    修复的必要性。若未来 SQLite 默认开启外键，此用例会失败，那时可整体删除
    本文件（说明 PRAGMA 已不再必要）。
    """
    eng, path = _make_engine(enable_fk=False)
    try:
        before, after = _seed_and_delete(eng)
        assert before == 1
        assert after == 1, "（对照）外键关闭时删车，快照残留为孤儿行——正是要修的洞"
    finally:
        eng.dispose()
        os.remove(path)
