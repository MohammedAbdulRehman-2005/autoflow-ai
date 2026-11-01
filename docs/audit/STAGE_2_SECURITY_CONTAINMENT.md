# Stage 2 Security Containment Report — AutoFlow AI X

**Date**: 2026-11-01  
**Author**: Senior Backend Security & Reliability Engineering Audit  
**Status**: ACTIVE & CONTAINED  
**Target Repository**: `autoflow-ai`  
**Phase**: Stage 2 Security Containment & Verification  

---

## 1. Executive Summary

During Stage 1 (`PRODUCTION_READINESS_AUDIT.md`), multiple critical security vulnerabilities and architectural hazards were identified in `autoflow-ai`. Stage 2 was initiated under a strict mandate: **contain the highest-risk issues, eliminate code execution vectors, protect endpoints, harden configuration, establish a reproducible test baseline on the target runtime (Python 3.11), and add regression test coverage without premature refactoring or Temporal redesign**.

All primary containment objectives have been executed and verified against automated regression suites:
- **Exposed Scratch Scripts Removed**: `query_db.py`, `check_hash.py`, and `extract_url.py` were removed from the working tree and permanently added to `.gitignore`.
- **Environment Leakage & Template Sandboxing Fixed**: Server OS environment variables were completely severed from `ExecutionContext` Jinja templates; `SandboxedEnvironment` and `StrictUndefined` were enabled to ensure missing variables and syntax errors fail explicitly.
- **Python `eval()` Removed**: Insecure dynamic evaluation in `ConditionBranchExecutor` was replaced with a restricted Abstract Syntax Tree (AST) parser permitting only deterministic boolean/comparison operators with zero arbitrary code execution capabilities.
- **Unauthenticated Endpoints Contained**: The open mail relay `/api/v1/gmail/test-send` was disabled (HTTP 410 Gone); cost-bearing routes `/api/v1/transcribe`, `/api/v1/ai/parse-intent`, and `/api/v1/followup/questions` were protected with `get_current_user` authentication and `slowapi` rate limiting.
- **SSRF Defense-in-Depth Implemented**: `HttpRequestExecutor` now validates schemes (HTTPS enforced), resolves hostnames via DNS, strictly blocks private/loopback/link-local/cloud metadata IPs, prohibits automatic HTTP redirects, and clamps response streams to a 5MB safety threshold.
- **Authentication & Configuration Hardened**: `Settings` now fails fast on startup in production if default/weak JWT secrets or missing encryption keys are detected; `FERNET_KEY` and `ENCRYPTION_KEY` were harmonized; OAuth state parameters were upgraded to 256-bit cryptographically secure single-use tokens; refresh token validation fails closed during Redis outages; CORS was restricted to explicit project origins.

---

## 2. Workstream A1: Exposed Credentials & Git History Remediation

### 2.1 Repository Cleanliness
In commit `916318b`, developer scratch scripts were inadvertently committed to the repository root:
1. `query_db.py`: Contained ad-hoc psycopg2 connection logic with hardcoded database credentials.
2. `check_hash.py`: Contained a bcrypt password verification script with literal hash test data.
3. `extract_url.py`: Inspected deployment URLs.

**Containment Actions Completed**:
- `query_db.py`, `check_hash.py`, and `extract_url.py` have been deleted from the working tree.
- `.gitignore` was updated to exclude `query_db.py`, `check_hash.py`, `extract_url.py`, and all SQLite/Postgres database files (`*.db`, `*.sqlite`, `*.sqlite3`).
- Added automated regression test `test_S2_SEC_001_scratch_scripts_removed_from_working_tree` and `test_S2_SEC_002_no_hardcoded_database_passwords_in_python_code` in `backend/tests/test_stage2_security.py` to prevent accidental reintroduction of hardcoded database credentials in application source code.

### 2.2 Git History Remediation Note & Owner Action
Deleting files from the current branch removes them from HEAD, but **does not erase them from Git history**. Commit `916318b9e37ecf812c31018f687a570775fe4a7e` and merge commit `fc4d22d` in `origin/main` and `origin/dev` retain the historical blobs.

> [!WARNING]
> In accordance with the Stage 2 non-negotiable rules:
> **Do not rewrite Git history until credentials have been rotated and a verified backup of the repository exists.**
> Rewriting history prior to credential rotation creates a false sense of security while active credentials remain compromised.

### 2.3 Secret-Rotation Checklist for Owner
The repository owner must execute the following credential rotation actions in production third-party dashboards:

- [ ] **Supabase Database Password**:
  1. Navigate to Supabase Dashboard -> Project Settings -> Database.
  2. Click **Reset Database Password**.
  3. Generate a new high-entropy (32+ character) password.
  4. Update `DATABASE_URL` in the production Render environment settings.
- [ ] **JWT Signing Secret (`JWT_SECRET_KEY`)**:
  1. Generate a 64-character random hex string: `python -c "import secrets; print(secrets.token_hex(32))"`.
  2. Update `JWT_SECRET_KEY` in Render environment settings.
  3. Note: Rotating the JWT key will invalidate all existing user sessions, requiring users to log in again.
- [ ] **Data Encryption Key (`FERNET_KEY` / `ENCRYPTION_KEY`)**:
  1. Documented in Section 6.2 below. Existing connected OAuth integrations are encrypted with the active key. Follow the phased re-encryption procedure before discarding the active key.
- [ ] **OAuth Application Secrets**:
  1. In Google Cloud Console, Slack App Management, Notion Developers, and HubSpot Developer portals, inspect client secrets and rotate if shared or exposed.
- [ ] **Git History Purge (Post-Rotation Only)**:
  1. Clone a fresh mirror: `git clone --mirror git@github.com:MohammedAbdulRehman-2005/autoflow-ai.git autoflow-backup`.
  2. Execute `git-filter-repo --invert-paths --paths-to-remove query_db.py --paths-to-remove check_hash.py --paths-to-remove extract_url.py`.
  3. Force push to remote only after team alignment.

---

## 3. Workstream A2: Unsafe Execution Path Containment

### 3.1 Template Engine Sandboxing & Environment Variable Isolation
**Location**: `backend/workflow/engine/context.py`

**Vulnerability Observed in Stage 1**:
`_build_jinja_vars()` previously included:
```python
"env": {k: v for k, v in os.environ.items()}
```
This directly leaked all backend environment variables (`DATABASE_URL`, `JWT_SECRET_KEY`, `FERNET_KEY`, `OPENAI_API_KEY`, `GROQ_API_KEY`) to any user constructing a workflow template expression like `{{env.DATABASE_URL}}`. Furthermore, `_SilentUndefined` was configured on Jinja2's `Environment`, silently returning empty strings for missing variables, which could alter branching logic without raising errors.

**Containment Implemented**:
1. **Zero Environment Leakage**: Removed `os.environ` from `jinja_ctx`. Replaced with `"env": {}`. Any template attempting to reference `{{env.ANYTHING}}` evaluates against an empty namespace and fails under `StrictUndefined`.
2. **Jinja2 SandboxedEnvironment**: Upgraded `_jinja_env` from standard `jinja2.Environment` to `jinja2.sandbox.SandboxedEnvironment` as defense-in-depth against template injection breakouts.
3. **Fail-Explicit Variable Resolution**: Removed `_SilentUndefined` and configured `undefined=StrictUndefined`. Defined `TemplateResolutionError(RuntimeError)`. In `_render_string()`, any `TemplateError` or `UndefinedError` raises `TemplateResolutionError`, halting execution explicitly instead of silently swallowing typos or missing fields.

### 3.2 Elimination of Python `eval()` in Condition Execution
**Location**: `backend/workflow/engine/executors/builtin.py`

**Vulnerability Observed in Stage 1**:
`ConditionBranchExecutor` attempted to evaluate condition expressions using:
```python
result = bool(eval(condition_raw, {"__builtins__": {}}, {}))
```
In Python, passing an empty `__builtins__` dictionary to `eval()` does **not** sandbox execution. Attackers can reach arbitrary code execution by traversing object attributes (e.g. `().__class__.__base__.__subclasses__()`).

**Containment Implemented**:
1. Completely purged `eval()` from `ConditionBranchExecutor`.
2. Implemented `evaluate_safe_condition(expr: str) -> bool` using Python's `ast` module.
3. The AST evaluator strictly accepts:
   - Literal values: strings, numbers, booleans, `None`.
   - Comparison operators: `==`, `!=`, `<`, `<=`, `>`, `>=`, `in`, `not in`, `is`, `is not`.
   - Boolean operators: `and`, `or`.
   - Unary operators: `not`, `+`, `-`.
   - Literals for `true`, `false`, `none`, `null` (case-insensitive).
4. Strictly rejects:
   - Function calls (`ast.Call`), attribute lookups (`ast.Attribute`), subscripts (`ast.Subscript`), comprehensions, lambdas, or imports.
5. Added configuration feature flag `UNSAFE_EVAL_ENABLED = False` in `Settings`. Any attempt to enable unsafe evaluation is blocked.
6. If an expression violates AST constraints or contains invalid syntax, `ConditionBranchExecutor` returns `ExecutorResult.fail(...)`.

---

## 4. Workstream A3: Unauthenticated Endpoints Containment

| Endpoint | Prior State | Containment Action | Resulting Behavior |
|---|---|---|---|
| `POST /api/v1/gmail/test-send` | Unauthenticated open email relay | Endpoint disabled | Returns `410 Gone`; email sending logic completely decoupled |
| `POST /api/v1/transcribe` | Unauthenticated audio processing calling Groq/OpenAI Whisper | Added `get_current_user` auth & `10/min` rate limit | Returns `401 Unauthorized` without token; protects provider credits |
| `POST /api/v1/ai/parse-intent` | Unauthenticated NLP prompt parser calling Gemini/Groq | Added `get_current_user` auth & `20/min` rate limit | Returns `401 Unauthorized` without token |
| `POST /api/v1/followup/questions` | Unauthenticated industry questionnaire generator | Added `get_current_user` auth & `30/min` rate limit | Returns `401 Unauthorized` without token |

**Supporting Module Improvements**:
- In `backend/intent_parser/gemini_followup.py`, the top-level module initialization `client = genai.Client(...)` was converted to lazy on-demand initialization `_get_client()`. This eliminated startup crashes during test runs or when `GEMINI_API_KEY` is not populated.
- In `frontend/src/pages/WorkflowBuilderPage.jsx`, voice recording transcription and parse-intent `fetch()` calls were updated to inject `Authorization: Bearer ${tokenStore.get()}`.

---

## 5. Workstream A4: HTTP Executor SSRF Containment

**Location**: `backend/workflow/engine/executors/http.py`

### 5.1 Application-Layer SSRF Protections
The generic HTTP executor now applies multi-tier SSRF validation before dispatching any network request:
1. **Scheme Whitelist**: Strict requirement for `https://`. Insecure `http://` is rejected unless `ALLOW_INSECURE_HTTP=true` is explicitly configured for isolated testing. Pseudo-schemes (`file://`, `gopher://`, `ftp://`, `data://`) are blocked immediately.
2. **DNS Resolution & IP Network Inspection**:
   - URL hostname is resolved using `socket.getaddrinfo()` to verify all resolved IPv4 and IPv6 addresses.
   - Evaluates each IP address against `ipaddress.ip_network` definitions covering:
     - IPv4 Loopback (`127.0.0.0/8`) and IPv6 Loopback (`::1/128`, `::ffff:0:0/96`)
     - Private networks (RFC 1918: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`; RFC 4193: `fc00::/7`)
     - Link-Local and Cloud Metadata (`169.254.0.0/16`, `fe80::/10`)
     - Reserved & Multicast ranges (`0.0.0.0/8`, `224.0.0.0/4`, `240.0.0.0/4`)
     - Explicit host blocklist: `metadata.google.internal`, `169.254.169.254`, `fd00:ec2::254`, `instance-data`.
3. **Redirect Prevention**: `follow_redirects=False` is set on `httpx.AsyncClient`. Any HTTP 3xx response returns an explicit failure, preventing attackers from bypassing IP checks via external redirectors.
4. **Response Size Threshold**: Response body streaming enforces `MAX_RESPONSE_BYTES = 5 * 1024 * 1024` (5MB). If the response stream exceeds 5MB, connection is terminated, preventing memory exhaustion DoS.
5. **Header Sanitization**: Forbids injection of spoofed internal routing headers (`Host`, `X-Forwarded-For`, `X-Forwarded-Host`, `X-Real-IP`).

### 5.2 Deployment-Level Egress Restrictions Required
Application-level DNS validation mitigates conventional SSRF. However, to eliminate Time-of-Check to Time-of-Use (TOCTOU) DNS rebinding risks completely:
- Production Render web services and worker processes should be deployed within an egress firewall or VPC egress proxy that blocks outbound traffic to link-local (`169.254.0.0/16`) and internal VPC ranges at the network packet filter layer.

---

## 6. Workstream A5: Authentication & Configuration Hardening

### 6.1 Production Fail-Fast Settings Validation
**Location**: `backend/core/config.py`

`Settings` now includes a Pydantic `model_validator(mode="after")` that triggers when `ENVIRONMENT` is set to `production`, `prod`, or `release`:
- **JWT Key**: Fails startup if `JWT_SECRET_KEY` contains `"change-me-in-production"` or has fewer than 32 characters.
- **Encryption Key**: Fails startup if neither `FERNET_KEY` nor `ENCRYPTION_KEY` is configured.
- **Unsafe Evaluation**: Fails startup if `UNSAFE_EVAL_ENABLED` is set to True.

### 6.2 Key Aliasing & Safe Re-encryption Migration Plan
**Configuration Mismatch Resolved**:
- `backend/core/config.py` defined `FERNET_KEY`.
- `backend/integrations/service.py` read `os.getenv("ENCRYPTION_KEY")`.

Both variables are now harmonized:
- `Settings` accepts either `FERNET_KEY` or `ENCRYPTION_KEY` and mirrors the value to both attributes.
- `_get_fernet()` checks `settings.FERNET_KEY`, `settings.ENCRYPTION_KEY`, `os.getenv("FERNET_KEY")`, and `os.getenv("ENCRYPTION_KEY")`.

**Re-encryption Procedure (When Rotating Encryption Keys)**:
Existing integration credentials in the `integrations` table are encrypted using the currently active key. To rotate keys without corrupting credentials:
1. Provide `OLD_ENCRYPTION_KEY` and `NEW_ENCRYPTION_KEY` in environment.
2. Run a migration script:
   ```python
   old_fernet = Fernet(os.environ["OLD_ENCRYPTION_KEY"].encode())
   new_fernet = Fernet(os.environ["NEW_ENCRYPTION_KEY"].encode())
   for row in db.query(Integration).all():
       decrypted = json.loads(old_fernet.decrypt(row.credentials_encrypted.encode()))
       row.credentials_encrypted = new_fernet.encrypt(json.dumps(decrypted).encode()).decode()
   db.commit()
   ```
3. Update `FERNET_KEY` to the new key and decommission the old key.

### 6.3 Cryptographically Secure Single-Use OAuth State
**Location**: `backend/integrations/service.py` & `backend/integrations/router.py`

**Prior State**:
`state = f"{user_id}:{provider}"` was predictable, forgeable, static, and lacked CSRF protection.

**Containment Implemented**:
- `generate_oauth_state(user_id, provider)` creates a 256-bit cryptographically random token (`secrets.token_urlsafe(32)`).
- Tokens are stored in a time-bounded state registry with a 10-minute TTL.
- `verify_and_consume_oauth_state(state, provider)` validates the provider association, verifies the TTL, and **deletes the token immediately** (single-use consumption). Replayed or tampered states are rejected.

### 6.4 Access Tokens in Query Strings
**Location**: `backend/integrations/router.py`

- The `GET /api/v1/integrations/{provider}/connect` route now prioritizes standard `Authorization: Bearer <token>` request headers over URL query parameters.
- If a query parameter token is detected, a security warning is logged, and the route remains compatible during frontend transition.

### 6.5 Fail-Closed Refresh Token Validation
**Location**: `backend/auth/service.py`

**Prior State**:
When Redis was unreachable during token refresh, `_validate_refresh_token_in_redis` returned `"FALLBACK"` and `refresh_access_token` treated the token as valid, bypassing revocation checks entirely (fail-open).

**Containment Implemented**:
When `stored_user_id == "FALLBACK"`, `refresh_access_token` logs a security alert and raises:
`ValueError("Authentication service temporarily unavailable to verify token revocation. Please sign in again.")` (fail-closed). Revoked tokens can never be refreshed during a cache outage.

### 6.6 CORS Hardening
**Location**: `backend/main.py`

1. **Origin Reflection Removed**: The exception handlers previously reflected any `Origin` header with `Access-Control-Allow-Credentials: true`. Replaced with `_is_origin_allowed(origin)` which only returns CORS headers if the origin strictly matches configured domains or the tightened regex.
2. **Regex Scope Narrowed**: Changed `allow_origin_regex` from wide-open `https://.*\.vercel\.app|http://localhost:\d+` to project-scoped `^https://autoflow-ai(-[a-zA-Z0-9_-]+)?\.vercel\.app$|^http://localhost:\d+$`.
