"""
AutoFlow AI X — Stage 2 Security Containment & Verification Tests
==================================================================
Verifies all Stage 2 security containments:
  1. Secret containment: No scratch scripts or hardcoded DB connection strings.
  2. Template engine: No OS env variable leakage, StrictUndefined fails explicitly.
  3. Expression execution: Python eval() removed, AST evaluator blocks code execution.
  4. HTTP Executor SSRF: Private IPs, loopback, cloud metadata, bad schemes, redirects blocked.
  5. Unauthenticated endpoints: /test-send returns 410, cost-bearing routes require auth.
  6. Auth & Config: Production fail-fast on weak/missing secrets, single-use OAuth state,
     fail-closed refresh token validation, and hardened CORS.
"""

import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.config import Settings
from backend.workflow.dsl.schema import WorkflowNodeDSL
from backend.workflow.engine.context import ExecutionContext, TemplateResolutionError
from backend.workflow.engine.executors.builtin import (
    ConditionBranchExecutor,
    evaluate_safe_condition,
)
from backend.workflow.engine.executors.http import (
    HttpRequestExecutor,
    validate_url_for_ssrf,
    is_ip_blocked,
)
from backend.integrations.service import (
    generate_oauth_state,
    verify_and_consume_oauth_state,
    _get_fernet,
)


# =============================================================================
# 1. Secret Containment & Repository Cleanliness
# =============================================================================

def test_S2_SEC_001_scratch_scripts_removed_from_working_tree():
    """Scratch scripts containing hardcoded credentials must not exist on disk."""
    for script_name in ["query_db.py", "check_hash.py", "extract_url.py"]:
        assert not os.path.exists(script_name), f"Forbidden scratch file '{script_name}' exists on disk!"


def test_S2_SEC_002_no_hardcoded_database_passwords_in_python_code():
    """Scan all application Python files (outside test suite) to ensure no hardcoded database connection credentials exist."""
    import re
    # Pattern detecting postgresql://user:password@host
    db_conn_pattern = re.compile(r"postgres(ql)?://[a-zA-Z0-9_\-]+:[^@\s\"'\\]+@[a-zA-Z0-9_\.\-]+")
    
    for root, _, files in os.walk("backend"):
        if "tests" in root or "__pycache__" in root:
            continue
        for fname in files:
            if fname.endswith(".py"):
                fpath = os.path.join(root, fname)
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    matches = db_conn_pattern.findall(content)
                    assert not matches, f"Hardcoded database credential URI detected in {fpath}!"



# =============================================================================
# 2. Template Security & Sandbox Containment (ExecutionContext)
# =============================================================================

def test_S2_SEC_003_template_engine_never_exposes_os_env():
    """Server OS environment variables must never be accessible in Jinja templates."""
    os.environ["SUPER_SECRET_TOKEN"] = "CLASSIFIED_DATABASE_SECRET_XYZ"
    
    ctx = ExecutionContext(
        run_id=uuid.uuid4(),
        trigger_payload={"user": "alice"},
        workflow_variables={},
    )
    
    # Resolving {{env.SUPER_SECRET_TOKEN}} must fail explicitly with StrictUndefined / TemplateResolutionError
    with pytest.raises(TemplateResolutionError):
        ctx.resolve("{{env.SUPER_SECRET_TOKEN}}")


def test_S2_SEC_004_template_engine_fails_explicitly_on_missing_variables():
    """Missing template variables must raise TemplateResolutionError rather than returning empty strings."""
    ctx = ExecutionContext(
        run_id=uuid.uuid4(),
        trigger_payload={},
        workflow_variables={},
    )
    with pytest.raises(TemplateResolutionError):
        ctx.resolve("{{nonexistent_node.output.missing_field}}")


def test_S2_SEC_005_template_engine_resolves_valid_context_safely():
    """Valid workflow context and payloads resolve correctly without errors."""
    ctx = ExecutionContext(
        run_id=uuid.uuid4(),
        trigger_payload={"email": "alice@example.com", "tier": "gold"},
        workflow_variables={"rate": 42},
    )
    ctx.set_node_output("step_1", {"status": "success", "count": 10})
    
    assert ctx.resolve("User: {{trigger.email}}") == "User: alice@example.com"
    assert ctx.resolve("{{step_1.output.count}}") == 10
    assert ctx.resolve("{{vars.rate}}") == 42


# =============================================================================
# 3. Condition Execution Security (ConditionBranchExecutor)
# =============================================================================

def test_S2_SEC_006_safe_condition_evaluates_valid_expressions():
    """Valid safe comparisons evaluate accurately."""
    assert evaluate_safe_condition("5 > 2") is True
    assert evaluate_safe_condition("10 <= 5") is False
    assert evaluate_safe_condition("'active' == 'active'") is True
    assert evaluate_safe_condition("'pending' != 'active'") is True
    assert evaluate_safe_condition("'gold' in ['bronze', 'silver', 'gold']") is True
    assert evaluate_safe_condition("'diamond' in ['bronze', 'silver', 'gold']") is False
    assert evaluate_safe_condition("true") is True
    assert evaluate_safe_condition("false") is False


def test_S2_SEC_007_condition_executor_blocks_code_execution():
    """Python arbitrary code execution payloads must be rejected."""
    executor = ConditionBranchExecutor()
    ctx = ExecutionContext(run_id=uuid.uuid4(), trigger_payload={}, workflow_variables={})
    node = WorkflowNodeDSL(id="cond_1", type="condition", service="builtin", operation="condition_branch", label="Test Cond")

    # Payloads attempting to traverse subclasses or call functions
    dangerous_payloads = [
        "().__class__.__base__.__subclasses__()",
        "__import__('os').system('echo pwned')",
        "eval('1 + 1')",
        "exec('import sys')",
        "open('/etc/passwd').read()",
    ]

    import asyncio
    for payload in dangerous_payloads:
        result = asyncio.run(executor.execute(node, ctx, {"condition": payload}))
        assert result.success is False, f"Dangerous payload was not blocked: {payload}"
        assert "Condition expression evaluation failed" in result.error


# =============================================================================
# 4. HTTP Executor SSRF Containment
# =============================================================================

def test_S2_SEC_008_ssrf_blocks_private_and_loopback_destinations():
    """Validate that local, private, and cloud metadata destinations are blocked."""
    forbidden_urls = [
        "http://localhost:8000/internal",
        "http://127.0.0.1:5432/",
        "http://127.0.0.100/secret",
        "http://[::1]/",
        "http://169.254.169.254/latest/meta-data/",
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://10.0.0.5/api",
        "http://172.16.0.1/admin",
        "http://192.168.1.1/router",
        "file:///etc/passwd",
        "gopher://127.0.0.1:6379/_INFO",
        "ftp://internal.server/data",
    ]

    for url in forbidden_urls:
        with pytest.raises(ValueError):
            validate_url_for_ssrf(url, allow_insecure_http=True)


def test_S2_SEC_009_ssrf_blocks_insecure_http_by_default():
    """HTTP without TLS is rejected unless ALLOW_INSECURE_HTTP is explicitly set."""
    with pytest.raises(ValueError, match="Only HTTPS requests are allowed"):
        validate_url_for_ssrf("http://example.com", allow_insecure_http=False)


def test_S2_SEC_010_http_executor_blocks_redirects():
    """HTTP executor rejects redirects to prevent redirect-based SSRF."""
    executor = HttpRequestExecutor()
    ctx = ExecutionContext(run_id=uuid.uuid4(), trigger_payload={}, workflow_variables={})
    node = WorkflowNodeDSL(id="http_1", type="action", service="builtin", operation="http_request", label="Outbound HTTP")

    import asyncio
    # Mock httpx response with redirect
    mock_response = MagicMock()
    mock_response.is_redirect = True
    mock_response.headers = {"location": "http://169.254.169.254/meta-data"}

    with patch("httpx.AsyncClient.stream") as mock_stream:
        mock_stream.return_value.__aenter__.return_value = mock_response
        result = asyncio.run(executor.execute(node, ctx, {"url": "https://example.com/redirect"}))
        assert result.success is False
        assert "HTTP Redirects are disabled" in result.error


# =============================================================================
# 5. Unauthenticated Endpoints Containment
# =============================================================================

def test_S2_SEC_011_gmail_test_send_disabled(client: TestClient):
    """The unauthenticated /api/v1/gmail/test-send endpoint must return 410 Gone."""
    resp = client.post("/api/v1/gmail/test-send?email=test@example.com")
    assert resp.status_code == 410
    assert "disabled" in resp.json()["detail"].lower()


def test_S2_SEC_012_transcribe_requires_authentication(client: TestClient):
    """The /api/v1/transcribe endpoint must reject unauthenticated requests with 401."""
    # Attempt upload without Authorization header
    resp = client.post(
        "/api/v1/transcribe",
        files={"audio": ("test.mp3", b"dummy audio content", "audio/mpeg")}
    )
    assert resp.status_code == 401


def test_S2_SEC_013_parse_intent_requires_authentication(client: TestClient):
    """The /api/v1/ai/parse-intent endpoint must reject unauthenticated requests with 401."""
    resp = client.post(
        "/api/v1/ai/parse-intent",
        json={"prompt": "When an email arrives, post to Slack"}
    )
    assert resp.status_code == 401


def test_S2_SEC_014_followup_questions_requires_authentication(client: TestClient):
    """The /api/v1/followup/questions endpoint must reject unauthenticated requests with 401."""
    resp = client.post(
        "/api/v1/followup/questions",
        json={"industry": "dental"}
    )
    assert resp.status_code == 401


# =============================================================================
# 6. Authentication, Configuration & CORS Security
# =============================================================================

def test_S2_SEC_015_production_settings_fail_fast_on_default_jwt_secret():
    """In production, default or weak JWT secrets must cause Settings validation to fail."""
    with pytest.raises(ValueError, match="Production deployment requires a cryptographically secure JWT_SECRET_KEY"):
        Settings(
            ENVIRONMENT="production",
            DATABASE_URL="postgresql://user:pass@localhost:5432/db",
            REDIS_URL="redis://localhost:6379/0",
            JWT_SECRET_KEY="change-me-in-production-use-a-long-random-string",
            FERNET_KEY="dGVzdC1mZXJuZXQta2V5LWZvci10ZXN0aW5nLW9ubHk=",
        )


def test_S2_SEC_016_production_settings_fail_fast_on_missing_encryption_key():
    """In production, missing FERNET_KEY/ENCRYPTION_KEY must fail fast."""
    with pytest.raises(ValueError, match="Production deployment requires FERNET_KEY"):
        Settings(
            ENVIRONMENT="production",
            DATABASE_URL="postgresql://user:pass@localhost:5432/db",
            REDIS_URL="redis://localhost:6379/0",
            JWT_SECRET_KEY="a" * 32,
            FERNET_KEY="",
            ENCRYPTION_KEY="",
        )


def test_S2_SEC_017_fernet_and_encryption_key_aliases(monkeypatch):
    """FERNET_KEY and ENCRYPTION_KEY are harmonized interchangeably."""
    key = "dGVzdC1mZXJuZXQta2V5LWZvci10ZXN0aW5nLW9ubHk="
    monkeypatch.delenv("FERNET_KEY", raising=False)
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)

    s1 = Settings(
        DATABASE_URL="sqlite:///test.db",
        REDIS_URL="redis://localhost:6379/0",
        FERNET_KEY=key,
    )
    assert s1.ENCRYPTION_KEY == key

    s2 = Settings(
        DATABASE_URL="sqlite:///test.db",
        REDIS_URL="redis://localhost:6379/0",
        ENCRYPTION_KEY=key,
    )
    assert s2.FERNET_KEY == key


class FakeAsyncRedis:
    def __init__(self, store=None):
        self.store = store if store is not None else {}
        self.ttls = {}

    async def setex(self, key, ttl, value):
        self.store[key] = value
        self.ttls[key] = ttl

    async def get(self, key):
        return self.store.get(key)

    async def delete(self, key):
        self.store.pop(key, None)

    async def eval(self, script, numkeys, key):
        # Emulate atomic GETDEL Lua script
        return self.store.pop(key, None)


@pytest.mark.asyncio
async def test_S2_SEC_018_single_use_oauth_state():
    """OAuth state tokens must be cryptographically unpredictable, stored in Redis, and single-use."""
    fake_redis = FakeAsyncRedis()
    test_user = uuid.uuid4()
    state = await generate_oauth_state(test_user, "slack", fake_redis)

    # State should be a random string, not predictable "user:provider"
    assert ":" not in state
    assert len(state) >= 32

    # First consumption succeeds
    consumed_user = await verify_and_consume_oauth_state(state, "slack", fake_redis)
    assert consumed_user == test_user

    # Second consumption must fail (atomic single-use replay rejection)
    with pytest.raises(ValueError, match="Invalid, expired, or previously consumed"):
        await verify_and_consume_oauth_state(state, "slack", fake_redis)


@pytest.mark.asyncio
async def test_S2_SEC_021_oauth_state_expiry():
    """Expired or missing OAuth state tokens are rejected."""
    fake_redis = FakeAsyncRedis()
    with pytest.raises(ValueError, match="Invalid, expired, or previously consumed"):
        await verify_and_consume_oauth_state("non_existent_or_expired_state", "slack", fake_redis)


@pytest.mark.asyncio
async def test_S2_SEC_022_oauth_state_wrong_provider():
    """OAuth state bound to provider A cannot be consumed with provider B."""
    fake_redis = FakeAsyncRedis()
    test_user = uuid.uuid4()
    state = await generate_oauth_state(test_user, "slack", fake_redis)

    with pytest.raises(ValueError, match="created for provider 'slack', not 'google'"):
        await verify_and_consume_oauth_state(state, "google", fake_redis)


@pytest.mark.asyncio
async def test_S2_SEC_023_oauth_state_multi_instance_and_restart():
    """OAuth state is multi-instance and restart-safe via shared durable store."""
    shared_redis_store = {}
    instance_a_redis = FakeAsyncRedis(store=shared_redis_store)
    instance_b_redis = FakeAsyncRedis(store=shared_redis_store)

    test_user = uuid.uuid4()
    state = await generate_oauth_state(test_user, "notion", instance_a_redis)

    # Instance B consumes state created by Instance A
    consumed_user = await verify_and_consume_oauth_state(state, "notion", instance_b_redis)
    assert consumed_user == test_user


@pytest.mark.asyncio
async def test_S2_SEC_024_oauth_state_controlled_failure_when_redis_unavailable():
    """When the backing state store is down, raise a typed controlled exception."""
    from backend.integrations.service import OAuthStateStoreUnavailableError

    failing_redis = AsyncMock()
    failing_redis.setex.side_effect = ConnectionError("Redis cluster unreachable")
    failing_redis.eval.side_effect = ConnectionError("Redis cluster unreachable")

    test_user = uuid.uuid4()
    with pytest.raises(OAuthStateStoreUnavailableError, match="OAuth state storage service is currently unavailable"):
        await generate_oauth_state(test_user, "slack", failing_redis)

    with pytest.raises(OAuthStateStoreUnavailableError, match="OAuth state storage service is currently unavailable"):
        await verify_and_consume_oauth_state("valid_token", "slack", failing_redis)


def test_S2_SEC_025_connect_endpoint_rejects_query_token(client: TestClient):
    """Passing tokens via query parameter on /{provider}/connect must be rejected with 400."""
    resp = client.get("/api/v1/integrations/google/connect?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
    assert resp.status_code == 400
    assert "query strings is prohibited" in resp.json()["detail"]


def test_S2_SEC_026_connect_endpoint_requires_bearer_auth(client: TestClient):
    """Initiating OAuth without Authorization header must return 401."""
    resp = client.get("/api/v1/integrations/google/connect")
    assert resp.status_code == 401


def test_S2_SEC_027_connect_endpoint_returns_json_url_with_bearer(client: TestClient, monkeypatch):
    """Authenticated connect endpoint returns JSON containing the authorization URL."""
    from backend.auth.dependencies import get_current_user
    from backend.auth.utils import create_access_token
    from backend.core.redis import get_redis
    test_user_id = uuid.uuid4()
    mock_user = MagicMock()
    mock_user.id = test_user_id
    mock_user.is_active = True
    mock_user.deleted_at = None
    fake_redis = FakeAsyncRedis()
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_redis] = lambda: fake_redis

    try:
        token = create_access_token(test_user_id)
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "mock-google-client-id")

        resp = client.get(
            "/api/v1/integrations/google/connect",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "url" in data
        assert "accounts.google.com" in data["url"]
        assert "state=" in data["url"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_redis, None)


@pytest.mark.asyncio
async def test_S2_SEC_028_ssrf_pins_actual_connection_destination():
    """SSRFPinningBackend records the verified IP to which outgoing TCP socket is pinned."""
    from httpcore._backends.anyio import AnyIOBackend
    from backend.workflow.engine.executors.http import SSRFPinningBackend

    backend = SSRFPinningBackend()
    with patch("socket.getaddrinfo") as mock_dns, \
         patch.object(AnyIOBackend, "connect_tcp", new_callable=AsyncMock) as mock_tcp:
        # Mock DNS returning a safe public IP
        mock_dns.return_value = [
            (2, 1, 6, "", ("93.184.216.34", 443))
        ]
        mock_tcp.return_value = MagicMock()

        await backend.connect_tcp("example.com", 443)
        assert backend.last_connected_ip == "93.184.216.34"
        # Assert the physical socket call was dispatched to the pinned IP
        mock_tcp.assert_awaited_once_with(
            host="93.184.216.34",
            port=443,
            timeout=None,
            local_address=None,
            socket_options=None,
        )


@pytest.mark.asyncio
async def test_S2_SEC_029_ssrf_blocks_loopback_and_metadata_at_connection_time():
    """SSRFPinningBackend blocks private and metadata destinations at TCP connection time."""
    from backend.workflow.engine.executors.http import SSRFPinningBackend

    backend = SSRFPinningBackend()
    with pytest.raises(ValueError, match="prohibited"):
        await backend.connect_tcp("169.254.169.254", 80)

    with pytest.raises(ValueError, match="Prohibited IP destination"):
        await backend.connect_tcp("127.0.0.1", 80)


def test_S2_SEC_030_ssrf_redacts_query_parameters_in_logs():
    """_redact_url_for_logs strips query parameters from request URLs."""
    from backend.workflow.engine.executors.http import _redact_url_for_logs

    url = "https://api.example.com/v1/data?token=secret_abc123&client_secret=super_secret"
    redacted = _redact_url_for_logs(url)
    assert "secret_abc123" not in redacted
    assert "super_secret" not in redacted
    assert "query=[REDACTED]" in redacted or "[REDACTED]" in redacted


def test_S2_SEC_031_ast_evaluator_exceeds_max_length():
    """Expressions exceeding MAX_EXPR_LENGTH (500 chars) are rejected."""
    long_expr = "1 == 1 and " * 100
    with pytest.raises(ValueError, match="exceeds maximum safety length"):
        evaluate_safe_condition(long_expr)


def test_S2_SEC_032_ast_evaluator_exceeds_max_nodes():
    """Expressions exceeding AST node limits are rejected."""
    many_nodes = " + ".join(["1"] * 60) + " == 60"
    with pytest.raises(ValueError, match="complexity exceeds safety limit"):
        evaluate_safe_condition(many_nodes)


def test_S2_SEC_033_ast_evaluator_exceeds_max_depth():
    """Deeply nested expressions are rejected to prevent recursion attacks."""
    nested = "not (" * 12 + "True" + ")" * 12
    with pytest.raises(ValueError, match="nesting depth"):
        evaluate_safe_condition(nested)


def test_S2_SEC_034_ast_evaluator_exceeds_collection_size():
    """Collections with more than 20 items are rejected."""
    big_list = str(list(range(25))) + " == []"
    with pytest.raises(ValueError, match="Collection size"):
        evaluate_safe_condition(big_list)


def test_S2_SEC_035_ast_evaluator_safe_type_mismatch():
    """Incompatible comparison types evaluate safely to False without crashing."""
    assert evaluate_safe_condition("'text' < 10") is False
    assert evaluate_safe_condition("5 > 'abc'") is False


def test_S2_SEC_036_production_error_returns_generic_message_and_correlation_id(client: TestClient, monkeypatch):
    """In production mode, unhandled 500 errors return a generic message and request ID."""
    from backend.auth.dependencies import get_current_user
    from backend.core.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.is_active = True
    mock_user.deleted_at = None
    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        with patch("backend.integrations.router.list_user_integrations") as mock_list:
            mock_list.side_effect = RuntimeError("Critical database connection failure with table schema_x")
            from backend.auth.utils import create_access_token
            token = create_access_token(mock_user.id)

            prod_client = TestClient(app, raise_server_exceptions=False)
            resp = prod_client.get("/api/v1/integrations/", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 500
            data = resp.json()
            assert "schema_x" not in data["detail"]
            assert "An internal server error occurred" in data["detail"]
            assert "request_id" in data
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_S2_SEC_037_correlation_id_middleware_sets_header(client: TestClient):
    """All HTTP responses include X-Request-ID header."""
    resp = client.get("/health")
    assert "x-request-id" in resp.headers


@pytest.mark.asyncio
async def test_S2_SEC_038_signup_fails_closed_when_redis_is_down():
    """If Redis fails during signup, unbacked tokens must not be returned and user creation rolls back."""
    from backend.auth.service import signup_user
    from backend.auth.schemas import SignupRequest

    failing_redis = AsyncMock()
    failing_redis.setex.side_effect = ConnectionError("Redis unavailable")
    mock_db = MagicMock()
    mock_db.query().filter().first.return_value = None

    payload = SignupRequest(email="newuser@example.com", password="Password123!", full_name="New User")

    with pytest.raises(RuntimeError, match="session store unavailable"):
        await signup_user(payload, mock_db, failing_redis)

    mock_db.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_S2_SEC_039_login_fails_closed_when_redis_is_down():
    """If Redis fails during login, unbacked tokens must not be returned."""
    from backend.auth.service import login_user
    from backend.auth.schemas import LoginRequest
    from backend.auth.utils import hash_password
    from backend.database.models import User

    failing_redis = AsyncMock()
    failing_redis.setex.side_effect = ConnectionError("Redis unavailable")
    mock_db = MagicMock()

    mock_user = MagicMock(spec=User)
    mock_user.id = uuid.uuid4()
    mock_user.email = "existing@example.com"
    mock_user.password_hash = hash_password("ValidPassword123!")
    mock_user.is_active = True
    mock_db.query().filter().first.return_value = mock_user

    payload = LoginRequest(email="existing@example.com", password="ValidPassword123!")

    with pytest.raises(RuntimeError, match="session store unavailable"):
        await login_user(payload, mock_db, failing_redis)


@pytest.mark.asyncio
async def test_S2_SEC_040_revoke_fails_closed_when_redis_is_down():
    """If Redis fails during token revocation, error is raised explicitly."""
    from backend.auth.service import logout_user
    from backend.auth.utils import create_refresh_token

    failing_redis = AsyncMock()
    failing_redis.delete.side_effect = ConnectionError("Redis unavailable")

    refresh_token = create_refresh_token(uuid.uuid4())
    with pytest.raises(RuntimeError, match="session store unavailable"):
        await logout_user(refresh_token, failing_redis)


def test_S2_SEC_019_refresh_token_fails_closed_when_redis_is_down():
    """If Redis is down, refresh token validation must fail closed rather than falling back."""
    from backend.auth.service import refresh_access_token
    from backend.auth.utils import create_refresh_token

    test_user_id = uuid.uuid4()
    refresh_token = create_refresh_token(test_user_id)

    # Mock Redis that fails with ConnectionError
    mock_redis = AsyncMock()
    mock_redis.get.side_effect = ConnectionError("Redis connection refused")
    mock_db = MagicMock()

    import asyncio
    with pytest.raises(ValueError, match="temporarily unavailable"):
        asyncio.run(refresh_access_token(refresh_token, mock_db, mock_redis))


def test_S2_SEC_020_cors_rejects_arbitrary_untrusted_origins(client: TestClient):
    """CORS middleware must not reflect arbitrary Origin headers with credentials."""
    resp = client.get(
        "/",
        headers={"Origin": "https://malicious-attacker.vercel.app"}
    )
    allow_origin = resp.headers.get("access-control-allow-origin")
    assert allow_origin != "https://malicious-attacker.vercel.app"
