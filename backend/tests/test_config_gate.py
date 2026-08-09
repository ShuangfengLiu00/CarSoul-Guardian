"""生产配置闸门回归测试（P0 安全修复 2026-08-09）。

守护的缺陷：``JWT_SECRET`` 曾带一个可用的默认占位值，生产环境忘配环境变量
时进程会**静默**用它起来，任何人都能照着公开仓库里的字符串伪造 JWT。

这类缺陷的特点是"不测就看不见" —— 没有报错、没有告警，功能全都正常。
所以必须有测试把它钉死：任何人把 fail-fast 闸门改回宽松，这里立刻变红。
"""
from __future__ import annotations

import pytest

from app.core import config as cfg
from app.core.config import (
    DEFAULT_JWT_SECRET,
    MIN_JWT_SECRET_LENGTH,
    ConfigurationError,
    Settings,
    _enforce_config_policy,
)

STRONG_SECRET = "x7Qm2Zk9Lp4Rt8Wv3Nc6Yb1Hd5Gf0Js2Ka7Me4Pu9Ro3Ti6Xz"  # 48 chars


@pytest.fixture
def warn_sink(caplog, capsys):
    """收集配置闸门发出的告警。

    ``_warn()`` 会根据"当前是否已有 logging handler"二选一地写 logging 或
    stderr（两条都写会导致告警重复输出）。pytest 自带 caplog handler，所以
    测试里通常走 logging；而直接跑 uvicorn 时走 stderr。两条路都要能断言到，
    否则测试会在"换了运行方式"时假绿。
    """
    caplog.set_level("WARNING", logger="carsoul.config")

    def _read() -> str:
        return caplog.text + capsys.readouterr().err

    return _read


def _build(monkeypatch, **env) -> Settings:
    """在干净的环境变量下构造 Settings（绕过 lru_cache 与模块级单例）。"""
    for key in ("APP_ENV", "ENVIRONMENT", "JWT_SECRET", "OPENAI_API_KEY",
                "REQUIRE_LLM", "DATABASE_URL", "CORS_ORIGINS"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    # env_file 里的值不能干扰断言，这里强制不读 .env
    return Settings(_env_file=None)


# --------------------------------------------------------------------------
# 开发模式：允许占位值，但必须告警
# --------------------------------------------------------------------------

def test_dev_allows_placeholder_secret(monkeypatch, warn_sink):
    s = _build(monkeypatch, ENVIRONMENT="development")
    assert s.JWT_SECRET == DEFAULT_JWT_SECRET
    _enforce_config_policy(s)  # 不应抛异常
    assert "WARNING" in warn_sink(), "开发模式必须打醒目告警，不能静默放行"


def test_dev_flags(monkeypatch):
    s = _build(monkeypatch, ENVIRONMENT="development")
    assert s.is_dev is True
    assert s.is_production is False


# --------------------------------------------------------------------------
# 生产模式：占位 / 弱密钥一律拒绝启动
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "secret",
    [
        "",                                    # 完全没配
        DEFAULT_JWT_SECRET,                    # config.py 的历史默认值
        "change-me-in-production",             # docker-compose.yml 的历史默认值
        "ci-test-secret",                      # CI 用的值（已进公开仓库）
        "0123456789abcdef",                    # 16 字符，长度不足
    ],
)
def test_production_rejects_weak_secret(monkeypatch, secret):
    s = _build(monkeypatch, APP_ENV="production", JWT_SECRET=secret)
    with pytest.raises(ConfigurationError) as exc:
        _enforce_config_policy(s)
    assert "JWT_SECRET" in str(exc.value)


def test_production_accepts_strong_secret(monkeypatch):
    s = _build(
        monkeypatch,
        APP_ENV="production",
        JWT_SECRET=STRONG_SECRET,
        DATABASE_URL="postgresql://u:p@db:5432/x",
        CORS_ORIGINS="https://carsoul.example.com",
    )
    assert len(STRONG_SECRET) >= MIN_JWT_SECRET_LENGTH
    assert _enforce_config_policy(s) is s  # 合规配置必须放行


# --------------------------------------------------------------------------
# 环境判定：fail closed
# --------------------------------------------------------------------------

@pytest.mark.parametrize("env_name", ["production", "prod", "staging", "prd", "PRODUCTION"])
def test_unknown_or_prod_env_is_treated_as_production(monkeypatch, env_name):
    """只有白名单里的开发环境名才放行，拼错/未知一律按生产处理。"""
    s = _build(monkeypatch, APP_ENV=env_name, JWT_SECRET="")
    assert s.is_production is True
    with pytest.raises(ConfigurationError):
        _enforce_config_policy(s)


@pytest.mark.parametrize("env_name", ["development", "dev", "local", "test", "testing"])
def test_non_production_envs_pass(monkeypatch, env_name):
    s = _build(monkeypatch, APP_ENV=env_name, JWT_SECRET="")
    assert s.is_production is False
    _enforce_config_policy(s)  # 不抛异常


def test_app_env_overrides_environment(monkeypatch):
    """APP_ENV 优先于历史字段 ENVIRONMENT。"""
    s = _build(monkeypatch, APP_ENV="production", ENVIRONMENT="development",
               JWT_SECRET=STRONG_SECRET)
    assert s.effective_env == "production"
    assert s.is_production is True


def test_no_split_brain_between_is_dev_and_is_production(monkeypatch):
    """曾经的真实 bug：APP_ENV=production 时 is_production=True 但 is_dev 也=True，
    导致 database/session.py 往生产库灌 demo 种子数据。两者不得同时为真。"""
    s = _build(monkeypatch, APP_ENV="production", ENVIRONMENT="development",
               JWT_SECRET=STRONG_SECRET)
    assert not (s.is_dev and s.is_production)
    assert s.is_dev is False


# --------------------------------------------------------------------------
# LLM 依赖策略
# --------------------------------------------------------------------------

def test_missing_llm_key_is_only_a_warning_by_default(monkeypatch, warn_sink):
    """默认放行：Agent/知识库本就设计为可优雅降级，缺 key 不算带病运行。"""
    s = _build(monkeypatch, APP_ENV="production", JWT_SECRET=STRONG_SECRET,
               OPENAI_API_KEY="")
    _enforce_config_policy(s)
    assert "OPENAI_API_KEY" in warn_sink()


def test_require_llm_makes_missing_key_fatal(monkeypatch):
    """显式声明 LLM 为硬依赖后，缺 key 必须拒绝启动。"""
    s = _build(monkeypatch, APP_ENV="production", JWT_SECRET=STRONG_SECRET,
               OPENAI_API_KEY="", REQUIRE_LLM="true")
    with pytest.raises(ConfigurationError) as exc:
        _enforce_config_policy(s)
    assert "REQUIRE_LLM" in str(exc.value)


# --------------------------------------------------------------------------
# 生产告警（不阻断，但必须出声）
# --------------------------------------------------------------------------

def test_production_warns_on_sqlite_and_localhost_cors(monkeypatch, warn_sink):
    s = _build(monkeypatch, APP_ENV="production", JWT_SECRET=STRONG_SECRET,
               DATABASE_URL="sqlite:///./prod.db",
               CORS_ORIGINS="http://localhost:5173")
    _enforce_config_policy(s)
    err = warn_sink()
    assert "SQLite" in err
    assert "CORS_ORIGINS" in err


def test_placeholder_blacklist_covers_known_leaked_values():
    """黑名单必须覆盖所有已进过公开仓库的密钥值。"""
    for leaked in (DEFAULT_JWT_SECRET, "change-me-in-production", "ci-test-secret"):
        assert leaked in cfg._PLACEHOLDER_JWT_SECRETS, f"{leaked} 未列入占位黑名单"


# --------------------------------------------------------------------------
# 全局鉴权中间件（Bearer 接线，2026-08-09 扩展）
# --------------------------------------------------------------------------

from app.core.auth import AuthMiddleware, PUBLIC_PATHS, _is_public  # noqa: E402


def test_public_allow_list_is_narrow_and_explicit():
    """豁免清单必须是窄且显式的常量，且覆盖登录/注册/文档/健康检查。"""
    for path in ("/health", "/docs", "/openapi.json", "/redoc",
                 "/api/user/login", "/api/user/register"):
        assert path in PUBLIC_PATHS, f"{path} 应在豁免清单中"
    # 业务路由绝不在豁免清单
    assert "/api/safety/gate-stats" not in PUBLIC_PATHS
    assert "/api/vehicle" not in PUBLIC_PATHS


def test_is_public_prefixes():
    """静态资源前缀也免鉴权（由 nginx 提供，后端不挂静态）。

    前缀匹配必须带边界：`/staticX`、`/assetsfoo` 这类**不是** `/static` 或
    `/assets` 目录的字符串，绝不能因前缀匹配被豁免——否则哪天加了
    `/staticdata/export` 端点就会静默无鉴权。
    """
    assert _is_public("/static/app.js") is True
    assert _is_public("/assets/logo.png") is True
    assert _is_public("/static") is True            # 前缀本身也算公共资源
    assert _is_public("/api/vehicle/1/state") is False
    assert _is_public("/staticX") is False          # 边界：不是 /static 目录
    assert _is_public("/assetsfoo") is False        # 边界：不是 /assets 目录
    assert _is_public("/staticdata/export") is False


def _client(monkeypatch):
    """用开发态占位密钥启动一个全新 app 实例，返回 TestClient。"""
    monkeypatch.setenv("ENVIRONMENT", "development")
    # 确保 app 在干净 env 下首次导入（settings 单例据此实例化）
    import importlib

    import app.main as main_mod
    importlib.reload(main_mod)
    from fastapi.testclient import TestClient

    return TestClient(main_mod.app)


def test_business_route_without_token_returns_401(monkeypatch):
    """任选一业务路由，无 token 必须 401，且 401 体不泄露 token / 期望格式。"""
    client = _client(monkeypatch)
    r = client.get("/api/safety/gate-stats")
    assert r.status_code == 401
    body = r.json()
    assert body == {"detail": "Unauthorized"}
    assert "Authorization" not in str(body)


def test_business_route_with_wrong_token_returns_401(monkeypatch):
    """带错误 token 必须 401（伪造/篡改/过期一律拒）。"""
    client = _client(monkeypatch)
    bad = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.not-a-real-signature"
    r = client.get(
        "/api/safety/gate-stats",
        headers={"Authorization": f"Bearer {bad}"},
    )
    assert r.status_code == 401
    assert r.json() == {"detail": "Unauthorized"}


def test_expired_token_returns_401(monkeypatch):
    """过期 token（签名有效，但 exp 早已过期）必须 401，与伪造 token 同等拒绝。

    关键：用和签发方同一把 ``settings.JWT_SECRET`` 造一个 exp 在 30 分钟前的
    JWT，签名是**真的有效**的——目的就是证明中间件走的是 ``decode_access_token``
    的真实过期校验，而不是靠签名错把过期的也拦了（那样会掩盖 exp 漏洞）。
    """
    import time

    from jose import jwt

    client = _client(monkeypatch)
    now = int(time.time())
    payload = {
        "sub": "1",
        "iat": now - 3600,
        "exp": now - 1800,  # 30 分钟前过期，签名仍有效
    }
    expired = jwt.encode(
        payload,
        cfg.settings.JWT_SECRET,
        algorithm=cfg.settings.JWT_ALGORITHM,
    )
    r = client.get(
        "/api/safety/gate-stats",
        headers={"Authorization": f"Bearer {expired}"},
    )
    assert r.status_code == 401
    assert r.json() == {"detail": "Unauthorized"}


def test_valid_token_passes_middleware(monkeypatch):
    """合法 token 必须穿过中间件（路由自身因依赖可能另有状态，但不应 401）。"""
    from app.core.security import create_access_token

    client = _client(monkeypatch)
    token = create_access_token(subject=1)
    r = client.get(
        "/api/safety/gate-stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code != 401, "合法 token 不应被中间件拦成 401"


def test_health_open_without_token(monkeypatch):
    """健康检查等豁免路径无需 token。"""
    client = _client(monkeypatch)
    r = client.get("/health")
    assert r.status_code == 200


def test_login_endpoint_not_blocked_by_middleware(monkeypatch):
    """登录端点本身必须免中间件拦截（路由层可能因凭证错误返回自己的 401/422，
    但绝不能是中间件那句 'Unauthorized'）。"""
    client = _client(monkeypatch)
    r = client.post("/api/user/login", json={})
    assert r.json().get("detail") != "Unauthorized", "中间件不应拦截登录端点"

