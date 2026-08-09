"""Application configuration.

Reads from environment / `.env`. Designed so the backend can boot in
development even without a running PostgreSQL (falls back to SQLite),
while production uses the real DATABASE_URL.

生产配置闸门（P0 安全修复 2026-08-09）
--------------------------------------
历史缺陷：``JWT_SECRET`` 带一个可用的默认占位值，生产环境忘配环境变量时
进程**静默**用该默认值起来，任何人都能照着开源仓库里的字符串伪造 JWT。
这类缺陷不会报错、不会告警，只会在被利用时才暴露 —— 属于商业化红线。

现策略（fail-fast，宁可起不来，不可带病运行）：
  * 生产模式（见 ``Settings.is_production``）下关键配置缺失/仍是占位值 →
    抛 ``ConfigurationError``，进程启动即退出，非 0 返回码。
  * 开发模式下允许占位值，但在 stderr 打醒目 WARNING 横幅，避免"开发时看
    不见、上线才踩雷"。
  * 环境判定优先读 ``APP_ENV``（部署侧惯用），回落到历史字段
    ``ENVIRONMENT``；**未知值一律按生产处理**（fail closed），避免把
    ``prod`` / ``prd`` / 拼错的值当成开发环境放行。
"""
from __future__ import annotations

import logging
import os
import sys
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_log = logging.getLogger("carsoul.config")

# 当前代码里的 JWT_SECRET 默认值。单独抽常量，便于黑名单与测试引用。
DEFAULT_JWT_SECRET = "please-change-me-to-a-random-secret"

# 占位密钥黑名单：只要生产环境命中其一，一律拒绝启动。
# 这里刻意把历史上真实出现过的值都列进来（config.py 的默认值、
# docker-compose.yml 的 `change-me-in-production`、CI 用的 `ci-test-secret`），
# 因为它们已经进过公开仓库 —— 等同于公开密钥。
_PLACEHOLDER_JWT_SECRETS = frozenset(
    {
        "",
        DEFAULT_JWT_SECRET,
        "change-me-in-production",
        "change-me",
        "changeme",
        "secret",
        "secret-key",
        "your-secret-key",
        "ci-test-secret",
        "test",
        "test-secret",
    }
)

# HS256 的密钥强度下限。32 字符 ≈ secrets.token_urlsafe(24) 的长度，
# 低于此长度的口令级密钥对离线暴力破解没有实质抵抗力。
MIN_JWT_SECRET_LENGTH = 32

# 被视为"非生产"的环境名。其余一切值（含空值以外的拼写变体）按生产处理。
_NON_PRODUCTION_ENVS = frozenset({"development", "dev", "local", "test", "testing"})

_SECRET_HOWTO = (
    'python -c "import secrets; print(secrets.token_urlsafe(48))"'
)


class ConfigurationError(RuntimeError):
    """生产环境配置不合法 —— 进程必须拒绝启动，而不是带病运行。"""


def _project_env() -> Path:
    """Locate the nearest .env file (project root, then backend/)."""
    here = Path(__file__).resolve()
    candidates = [
        here.parent.parent.parent / ".env",   # project root
        here.parent.parent / ".env",          # backend/
    ]
    for c in candidates:
        if c.exists():
            return c
    return here.parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_project_env()),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---------- Environment ----------
    ENVIRONMENT: str = "development"

    # ---------- Database ----------
    # If it does not start with postgres, we fall back to SQLite for dev.
    DATABASE_URL: str = "sqlite:///./carsoul_dev.db"

    # ---------- Redis ----------
    REDIS_URL: str = "redis://localhost:6379/0"

    # ---------- Security ----------
    JWT_SECRET: str = "please-change-me-to-a-random-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ---------- AI / LLM ----------
    OPENAI_API_KEY: str = ""
    MODEL_NAME: str = "gpt-4o-mini"
    OPENAI_API_BASE: str = ""

    # LLM 是否为硬依赖。
    # 默认 False：本系统的 Agent / 知识库是**刻意**设计成可优雅降级的
    # （无 key → 规则专家团 + hash embedding，功能可用、质量下降），
    # 所以缺 key 不构成"带病运行"，只警告不拦截。
    # 若某次部署把 LLM 问答当作对外承诺的核心能力，就把它设成 true，
    # 缺 key 时与 JWT_SECRET 同等待遇 —— 启动即拒。
    REQUIRE_LLM: bool = False

    # ---------- Agent ----------
    AGENT_LANGUAGE: str = "zh-CN"
    AGENT_PROACTIVE: bool = True

    # ---------- CarSoul World Model (carModel) bridge ----------
    # Guardian 通过 HTTP 调用 carModel 车辆世界模型引擎，拿到真实的
    # SOH / 故障 / 残值 / 反事实预测。引擎默认跑在 :8000（见 start.sh）。
    CARSOUL_WORLD_API_URL: str = "http://localhost:8000"

    # Dashboard ``/api/health/overview`` 在调用方没指定 vehicle_id 时使用的
    # 缺省 carModel 车辆（如 "CS001"）。**默认留空**：Guardian 的车辆表与
    # carModel 的 vehicle_id 之间目前没有映射关系，没人指定车就意味着拿不到
    # 真实车况 —— 那就如实显示"暂无数据"，绝不拿一辆随便挑的车冒充"本车"。
    # 演示需要真实数据时，在 .env 里显式指定一辆真车。
    CARSOUL_WORLD_DEFAULT_VEHICLE_ID: str = ""

    # ---------- Knowledge base ----------
    VECTOR_DB_PATH: str = "./ai-agent/memory/vector_store"
    CHROMA_COLLECTION: str = "carsoul_guardian"

    # ---------- CORS ----------
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def effective_env(self) -> str:
        """生效的环境名：APP_ENV 优先，回落 ENVIRONMENT，再回落 development。"""
        return (os.getenv("APP_ENV") or self.ENVIRONMENT or "development").strip().lower()

    @property
    def is_dev(self) -> bool:
        """是否开发模式。

        判定口径保持不变 —— 只有精确的 ``development`` 才算 dev，因为
        ``database/session.py:69`` 用它决定是否灌 demo 种子数据，放宽会让
        staging 被塞进演示数据。

        唯一的改动是从 ``ENVIRONMENT`` 换成 ``effective_env``：否则设了
        ``APP_ENV=production`` 但没设 ``ENVIRONMENT`` 时，会出现
        ``is_production=True`` 与 ``is_dev=True`` 同时成立的裂脑状态 ——
        实测确实往生产库里灌了 demo 种子数据。
        只用 ``ENVIRONMENT`` 的既有部署行为完全不变（此时两者等价）。
        """
        return self.effective_env == "development"

    @property
    def is_production(self) -> bool:
        """是否按生产口径做配置校验。

        判定为 **fail closed**：只有明确列在 ``_NON_PRODUCTION_ENVS`` 里的
        环境名才算非生产，其余（production / prod / staging / 拼错的值）
        统统按生产处理。宁可让开发者多配一个变量，也不能让线上漏过闸门。
        """
        return self.effective_env not in _NON_PRODUCTION_ENVS

    @property
    def jwt_secret_is_placeholder(self) -> bool:
        return self.JWT_SECRET.strip() in _PLACEHOLDER_JWT_SECRETS

    @property
    def effective_database_url(self) -> str:
        """Return a SQLAlchemy URL; force sqlite in dev if no PG available."""
        url = self.DATABASE_URL.strip()
        if url.startswith(("postgresql", "postgres+psycopg")):
            return url
        # Dev fallback: SQLite (file-based so data persists across reloads)
        if not url:
            return "sqlite:///./carsoul_dev.db"
        return url


def _warn(msg: str) -> None:
    """开发模式告警。

    直接写 stderr 而不是走 loguru：``app/utils/logger.py`` 反过来 import 本
    模块，配置阶段 loguru 还没配好，用它会有循环依赖和"日志丢在配置之前"
    的问题。stderr 在任何启动方式下（uvicorn / pytest / docker）都可见。
    """
    if _log.hasHandlers():
        # 已有日志配置（例如宿主应用接管了 root logger）→ 走正规日志管道。
        _log.warning(msg)
    else:
        # 无 handler 时 logging 会退化到 lastResort 也打 stderr，
        # 两条路都走会导致告警重复输出一遍，所以这里二选一。
        print(msg, file=sys.stderr, flush=True)


def _collect_production_problems(s: Settings) -> list[str]:
    """列出生产环境下**必须**阻断启动的配置问题。"""
    problems: list[str] = []

    secret = s.JWT_SECRET.strip()
    if s.jwt_secret_is_placeholder:
        problems.append(
            "JWT_SECRET 未配置或仍是占位值。该值已随代码进入公开仓库，"
            "等同于把签名密钥公开 —— 任何人都能伪造任意用户的登录令牌。\n"
            f"    生成一个：{_SECRET_HOWTO}"
        )
    elif len(secret) < MIN_JWT_SECRET_LENGTH:
        problems.append(
            f"JWT_SECRET 长度 {len(secret)} < {MIN_JWT_SECRET_LENGTH}，"
            "强度不足以抵抗离线暴力破解。\n"
            f"    生成一个：{_SECRET_HOWTO}"
        )

    if s.REQUIRE_LLM and not s.OPENAI_API_KEY.strip():
        problems.append(
            "REQUIRE_LLM=true 但 OPENAI_API_KEY 为空。既然把 LLM 声明为硬依赖，"
            "就不能带着降级模式上线（用户会拿到规则模板回复却以为是大模型）。\n"
            "    要么配置 key，要么把 REQUIRE_LLM 设为 false 并接受降级语义。"
        )

    return problems


def _collect_production_warnings(s: Settings) -> list[str]:
    """生产环境下值得警告、但不足以阻断启动的问题。"""
    warnings: list[str] = []

    url = s.effective_database_url
    if url.startswith("sqlite"):
        warnings.append(
            f"生产环境正在使用 SQLite（{url}）。单写入者、无网络访问、"
            "备份即拷文件 —— 单机小流量可接受，多副本/高并发场景必须换 PostgreSQL。"
        )
    if "carsoul:carsoul@" in url:
        warnings.append(
            "DATABASE_URL 使用示例账号密码 carsoul:carsoul，生产环境请改掉。"
        )

    if not s.OPENAI_API_KEY.strip():
        warnings.append(
            "OPENAI_API_KEY 为空：Agent 走规则专家团、知识库走 hash embedding。"
            "功能可用但答案质量下降，对外承诺 LLM 能力前请确认这是有意为之"
            "（需要强制拦截就设 REQUIRE_LLM=true）。"
        )

    localhost_origins = [o for o in s.cors_origins_list if "localhost" in o or "127.0.0.1" in o]
    if localhost_origins:
        warnings.append(
            f"生产环境 CORS_ORIGINS 仍包含本地来源 {localhost_origins}，"
            "上线前应收敛为真实域名。"
        )

    return warnings


def _enforce_config_policy(s: Settings) -> Settings:
    """启动期配置闸门。生产不合格直接抛错；开发只警告。"""
    if not s.is_production:
        if s.jwt_secret_is_placeholder:
            _warn(
                "\n"
                "  ============================================================\n"
                "   [WARNING] JWT_SECRET 正在使用占位默认值\n"
                "   当前环境: %s（非生产，故放行）\n"
                "   该密钥是公开的，签发的令牌毫无安全性可言，仅供本地开发。\n"
                "   部署到生产前必须配置真实密钥，否则进程将拒绝启动：\n"
                "     %s\n"
                "  ============================================================\n"
                % (s.effective_env, _SECRET_HOWTO)
            )
        return s

    for w in _collect_production_warnings(s):
        _warn(f"[WARNING][production] {w}")

    problems = _collect_production_problems(s)
    if problems:
        detail = "\n".join(f"  {i}. {p}" for i, p in enumerate(problems, 1))
        raise ConfigurationError(
            "\n"
            "============================================================\n"
            f" 生产配置校验未通过（APP_ENV/ENVIRONMENT = {s.effective_env}）\n"
            " 进程拒绝启动 —— 这是刻意的：带着不安全配置跑起来，\n"
            " 比起不来危险得多。\n"
            "------------------------------------------------------------\n"
            f"{detail}\n"
            "------------------------------------------------------------\n"
            " 本地开发请显式声明环境：APP_ENV=development（或 ENVIRONMENT=development）\n"
            "============================================================"
        )

    return s


@lru_cache
def get_settings() -> Settings:
    return _enforce_config_policy(Settings())


settings = get_settings()
