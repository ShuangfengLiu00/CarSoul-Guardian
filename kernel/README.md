# carsoul-runtime

CarSoul OS Runtime SDK — 开发者面向的 Agent 运行时门面。

## 安装

```bash
pip install -e kernel/
```

## Quick Start（≤20 行）

```python
from carsoul_os import (
    create_agent, register_skill, execute_workflow,
    GovernanceProfile, Skill, SkillFinding,
)
from vehicle_protocol.simulator import create_virtual_vehicle

# 1. 创建虚拟车并生成遥测数据
vehicle = create_virtual_vehicle("family_ev", seed=42)
frames = vehicle.run(days=30)

# 2. 创建守护 Agent（默认只读治理）
agent = create_agent(
    name="my_guardian",
    memory="sqlite:///carsoul.db",       # 持久化记忆
    governance=GovernanceProfile(read_only=True),
)

# 3. 执行诊断工作流
result = execute_workflow(agent, frames, "电池最近怎么样")
print(result.answer)
print(f"灵魂指数: {result.soul_score:.1f} ({result.grade})")
print(f"异常: {len(result.anomalies)} 项")
print(f"专家建议: {len(result.skill_findings)} 条")
```

## 核心 API

| API | 说明 |
|-----|------|
| `create_agent(name, skills, memory, governance)` | 创建自定义 Agent |
| `register_skill(skill)` | 注册自定义诊断技能 |
| `execute_workflow(agent, frames, query)` | 执行诊断工作流 |
| `GovernanceProfile(read_only=True)` | 治理配置（只读白名单） |
| `Skill` | 技能协议接口 |
| `SkillFinding` | 结构化技能输出 |
| `WorkflowResult` | 工作流结果（含 answer / anomalies / skill_findings / trace） |

## 内置专家技能

10 个专家技能可通过 `register_all_expert_skills()` 一键注册：

| 技能 | 领域 | 说明 |
|------|------|------|
| powertrain_skill | 动力系统 | 电池/电机/发动机诊断 |
| chassis_skill | 底盘系统 | 刹车/轮胎/悬挂 |
| electrical_skill | 电气系统 | 传感器/电路 |
| driving_behavior_skill | 驾驶行为 | 驾驶习惯分析 |
| maintenance_skill | 保养规划 | 保养周期/成本 |
| vehicle_value_skill | 车辆价值 | 折旧/保值率 |
| environment_skill | 环境适应 | 温度/天气/路况 |
| charging_skill | 充电智能 | SOC/充电策略 |
| energy_optimization_skill | 能耗优化 | 驾驶风格/能效 |
| user_companion_skill | 用户陪伴 | 个性化建议 |

## Agent 预设

5 个预设技能组合：

- `guardian` — 全量 10 技能（守护者）
- `battery_agent` — 动力+底盘+充电（电池专家）
- `safety_agent` — 底盘+驾驶+环境（安全专家）
- `value_agent` — 价值+保养+陪伴（估值专家）
- `energy_agent` — 充电+能耗（能耗专家）

## 自定义技能

```python
from carsoul_os import register_skill, Skill, SkillFinding

class MyBatterySkill:
    name = "my_battery_check"
    domain = "battery"
    def match(self, state):
        return "battery" in state.get("anomaly_topics", [])
    def run(self, state, tools, memory, knowledge=None):
        return SkillFinding(
            specialty="battery",
            recommendation="检查电池冷却系统",
            confidence=0.85,
        )

register_skill(MyBatterySkill())
```

## 测试

```bash
cd kernel
python -m pytest tests/ -v
```

## License

MIT
