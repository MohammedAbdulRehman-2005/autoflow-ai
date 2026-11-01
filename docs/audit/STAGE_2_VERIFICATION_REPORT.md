# Stage 2 Verification Report — AutoFlow AI X

**Date**: 2026-11-01  
**Author**: Senior Backend Security & Reliability Engineering Audit  
**Status**: COMPLETE  
**Stage 2 Exit Decision**: **PASS (CONDITIONAL ON OWNER CREDENTIAL ROTATION)**  

---

## 1. Test Environment Specification

To resolve the environmental and dependency blockers identified during Stage 1, a clean, isolated virtual environment was initialized strictly adhering to the project's production runtime target (Python 3.11):

| Parameter | Specification / Value |
|---|---|
| **Operating System** | Windows 11 Pro / PowerShell 7.x |
| **Python Runtime** | CPython 3.11.16 (64-bit) managed via `uv 0.12.18` |
| **Virtual Environment Path** | `d:\autoflow-ai\.venv` |
| **Core Packages Installed** | fastapi 0.162.0, sqlalchemy 2.1.6, pydantic 2.14.2, httpx 0.27.2, jinja2 3.1.6, celery 5.6.3, langgraph 1.2.19, sentry-sdk 2.73.0, slowapi 0.1.10, redis 6.4.0, pytest 9.2.0, pytest-asyncio 1.4.1, pytest-cov 7.1.0 (115 total packages) |
| **Database Target for Tests** | Disposable local SQLite test database (`sqlite:///./test.db`) / Mocked engines; **0% connection to production Supabase** |
| **Redis Target for Tests** | Isolated mock / local loopback |

---

## 2. Test Execution Commands & Verified Baseline Results

### 2.1 Execution Commands
```powershell
# Set safe, isolated test environment variables (strictly non-production)
$env:DATABASE_URL="sqlite:///./test.db"
$env:REDIS_URL="redis://127.0.0.1:6379/0"
$env:JWT_SECRET_KEY="test-jwt-secret-key-for-testing-only-1234567890"
$env:FERNET_KEY="dGVzdC1mZXJuZXQta2V5LWZvci10ZXN0aW5nLW9ubHk="
$env:GROQ_API_KEY="test-key"
$env:OPENAI_API_KEY="test-key"
$env:GEMINI_API_KEY="test-gemini-key"

# Run complete backend test suite
.venv\Scripts\python.exe -m pytest backend/tests -v
```

### 2.2 Verified Quantitative Summary

```
============================= test session starts =============================
platform win32 -- Python 3.11.16, pytest-9.2.0, pluggy-1.7.0 -- D:\autoflow-ai\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\autoflow-ai
plugins: anyio-4.16.0, langsmith-0.8.5, asyncio-1.4.1, cov-7.1.0
collected 101 items

Total Tests Collected : 101
Passed               : 100
Skipped              : 1 (test_S2_016_sprint1_regression_mutation_service: frontend JS test skipped in python)
Failed               : 0
Errors               : 0
Execution Duration   : 3.21s
================== 100 passed, 1 skipped, 1 warning in 3.21s ==================
```

### 2.3 Breakdown by Test Module

| Module | Purpose | Tests | Passed | Skipped | Failed |
|---|---|:---:|:---:|:---:|:---:|
| `backend/tests/test_health.py` | FastAPI application health probe and lifespan verification | 1 | 1 | 0 | 0 |
| `backend/tests/test_sprint1.py` | DSL version fields, `WorkflowContext`, credential resolution, node registry lookups, condition key validation, event bus | 32 | 32 | 0 | 0 |
| `backend/tests/test_sprint2.py` | Error policies, single node execution, secret scrubbing, error classification, node metadata, calendar doc_url | 23 | 22 | 1 | 0 |
| `backend/tests/test_sprint3.py` | Capability registry, editor engine delta computation, AST safe IDs, patch application | 25 | 25 | 0 | 0 |
| `backend/tests/test_stage2_security.py` | **NEW: Complete Stage 2 security regression test suite** | 20 | 20 | 0 | 0 |
| **Total** | | **101** | **100** | **1** | **0** |

---

## 3. Summary of Code & Configuration Changes Made

### Files Deleted (Purging Exposed Material from Working Tree)
1. `query_db.py`: Removed hardcoded database connection script.
2. `check_hash.py`: Removed sensitive bcrypt testing script.
3. `extract_url.py`: Removed sensitive URL extraction script.

### Files Modified & Security Containments Applied
1. [`.gitignore`](file:///d:/autoflow-ai/.gitignore): Added `query_db.py`, `check_hash.py`, `extract_url.py`, and `*.db`, `*.sqlite`, `*.sqlite3` to prevent re-committing scratch tools or databases.
2. [`backend/core/config.py`](file:///d:/autoflow-ai/backend/core/config.py):
   - Added production fail-fast validators for default/weak `JWT_SECRET_KEY` and missing encryption keys.
   - Harmonized `FERNET_KEY` and `ENCRYPTION_KEY` as bi-directional aliases.
   - Added feature flags `UNSAFE_EVAL_ENABLED=False` and `ALLOW_INSECURE_HTTP=False`.
3. [`backend/workflow/engine/context.py`](file:///d:/autoflow-ai/backend/workflow/engine/context.py):
   - Severed OS environment variables (`os.environ`) from Jinja template rendering (`"env": {}`).
   - Enabled `jinja2.sandbox.SandboxedEnvironment` and `StrictUndefined`.
   - Defined `TemplateResolutionError` so undefined variables fail explicitly rather than silently defaulting to empty strings.
4. [`backend/workflow/engine/executors/builtin.py`](file:///d:/autoflow-ai/backend/workflow/engine/executors/builtin.py):
   - Completely removed Python `eval()` from `ConditionBranchExecutor`.
   - Added AST-based safe condition evaluator supporting only pure comparison/logical operations without code execution capabilities.
5. [`backend/workflow/engine/executors/http.py`](file:///d:/autoflow-ai/backend/workflow/engine/executors/http.py):
   - Added scheme enforcement (`https://` required).
   - Added DNS-based IP validation blocking private/loopback/link-local/metadata IP addresses.
   - Disabled automatic redirects (`follow_redirects=False`) to prevent redirect-based SSRF.
   - Added streaming response size cap (`MAX_RESPONSE_BYTES = 5MB`).
   - Sanitized spoofable routing headers.
6. [`backend/gmail/router.py`](file:///d:/autoflow-ai/backend/gmail/router.py):
   - Permanently disabled the open email relay endpoint `POST /api/v1/gmail/test-send` (returns `410 Gone`).
7. [`backend/routes/transcribe.py`](file:///d:/autoflow-ai/backend/routes/transcribe.py):
   - Protected `/api/v1/transcribe` with `get_current_user` authentication and `10/min` rate limit.
8. [`backend/intent_parser/router.py`](file:///d:/autoflow-ai/backend/intent_parser/router.py):
   - Protected `/api/v1/ai/parse-intent` with `get_current_user` authentication and `20/min` rate limit.
9. [`backend/intent_parser/gemini_followup.py`](file:///d:/autoflow-ai/backend/intent_parser/gemini_followup.py):
   - Replaced top-level `genai.Client(...)` crash on missing API key with lazy `_get_client()` initialization.
10. [`backend/followup_engine/router.py`](file:///d:/autoflow-ai/backend/followup_engine/router.py):
    - Protected `/api/v1/followup/questions` with `get_current_user` authentication and `30/min` rate limit.
11. [`backend/integrations/service.py`](file:///d:/autoflow-ai/backend/integrations/service.py):
    - Updated `_get_fernet()` to accept both `FERNET_KEY` and `ENCRYPTION_KEY`.
    - Implemented 256-bit single-use cryptographic OAuth state generation and validation with 10-minute expiration.
12. [`backend/integrations/router.py`](file:///d:/autoflow-ai/backend/integrations/router.py):
    - Supported standard `Authorization: Bearer <token>` request headers on `/{provider}/connect` and deprecated query string token transmission.
13. [`backend/auth/service.py`](file:///d:/autoflow-ai/backend/auth/service.py):
    - Converted refresh token validation to fail-closed during Redis outages.
14. [`backend/main.py`](file:///d:/autoflow-ai/backend/main.py):
    - Removed arbitrary `Origin` header reflection in exception handlers.
    - Narrowed CORS regex to project domains and local dev ports.
15. [`backend/workflow/node_registry.py`](file:///d:/autoflow-ai/backend/workflow/node_registry.py):
    - Added missing `doc_url` documentation references to `google_calendar.create_event` and `google_calendar.list_events`, resolving legacy test S2_011.
16. [`frontend/src/pages/WorkflowBuilderPage.jsx`](file:///d:/autoflow-ai/frontend/src/pages/WorkflowBuilderPage.jsx):
    - Injected `Authorization: Bearer ${tokenStore.get()}` into transcribe and parse-intent `fetch()` calls.

### New Test Suites Created
1. [`backend/tests/test_stage2_security.py`](file:///d:/autoflow-ai/backend/tests/test_stage2_security.py): 20 automated security regression tests covering scratch script absence, secret leakage prevention, template isolation, AST evaluator safety, SSRF blocking, endpoint authentication, production configuration fail-fast, single-use OAuth state, fail-closed auth, and CORS hardening.

---

## 4. Workstream C: Focused Remaining Audit Findings

During Stage 2, focused dynamic and static inspections were conducted across remaining modules:

| Finding ID | Component & Location | Observed Behavior | Impact | Dynamic / Static | Severity | Confidence | Recommended Remediation |
|---|---|---|---|:---:|:---:|:---:|---|
| **FIND-C01** | `executors/google_sheets.py` (Lines 49–75, 107–114) | Google Sheets API calls are commented out; executor returns hardcoded empty/fake dicts (`# STUB`) | **Critical Functional Defect**: Workflows executing Google Sheets steps appear to succeed but make zero API calls. | Dynamic & Static | **High** | 100% | Implement real Google Sheets v4 API calls via `googleapiclient` or HTTP using authenticated access tokens. |
| **FIND-C02** | `executors/google_drive.py` (Lines 92–95) | When Google Drive API fails or token is missing, executor returns `ExecutorResult.ok` with fake ID `drive_folder_<uuid>` | **Silent Failure / Phantom State**: Workflows believe folders/files were created in Google Drive when they failed, corrupting downstream state. | Static | **High** | 100% | Return `ExecutorResult.fail()` immediately upon API error or missing credentials. Never fake success. |
| **FIND-C03** | `executors/hubspot.py` (Lines 29–62) | Access token is retrieved from credentials blob without verifying expiration or refreshing it | **Authentication Failure**: HubSpot OAuth access tokens expire after 30 minutes. All executions fail 30m after connection. | Static | **High** | 100% | Implement automated token refresh via HubSpot OAuth token endpoint using the stored `refresh_token`. |
| **FIND-C04** | `executors/gmail.py` (Lines 89–131) | Google OAuth token refresh succeeds in memory but the refreshed token is not persisted back to the database | **Performance / Quota Exhaustion**: Every subsequent node execution re-executes an HTTP token refresh against Google. | Static | **Medium** | 100% | Persist refreshed access tokens and updated expiration timestamps back to the `integrations` table. |
| **FIND-C05** | `crud/router.py` (Lines 62–71, 95–160) | Workflow creation (`POST /api/v1/workflows`) accepts arbitrary `dsl_json` dicts without running `WorkflowDSL` or graph validation | **Data Integrity Hazard**: Corrupted, cyclic, or invalid DSL graphs can be persisted and later trigger scheduler/engine crashes. | Static | **Medium** | 100% | Add `validate_workflow_graph(WorkflowDSL.model_validate(body.dsl_json))` validation before committing to database. |
| **FIND-C06** | `executors/slack.py`, `notion.py`, `hubspot.py` | Outbound integration requests lack rate-limiting backoff (HTTP 429) or idempotency keys | **Duplicate Side Effects & Throttling**: Burst executions fail abruptly when provider rate limits are exceeded. | Static | **Medium** | 95% | Wrap external API calls in bounded exponential backoff with `Retry-After` header inspection (prepared for Temporal activities in Stage 3). |

---

## 5. Unresolved Security Issues & Owner Actions Required

The application codebase on branch `feature/stage2-frontend` is safely contained. However, the following operational and infrastructure actions **require explicit owner execution** before promoting to production:

1. **Production Credential Rotation**:
   - Supabase PostgreSQL password must be rotated in the Supabase Dashboard.
   - Production `JWT_SECRET_KEY` must be generated and configured in Render.
   - Production `FERNET_KEY` must be configured in Render.
2. **Git History Scrubbing (Post-Rotation Only)**:
   - Git history retains commits `916318b` and `fc4d22d`. Once the Supabase password has been rotated in production, the owner should run `git-filter-repo` on a verified backup repository and force-push clean branches.
3. **Render Staging Web Service Provisioning**:
   - Create `autoflow-ai-staging` web service and `autoflow-ai-staging` Supabase database as detailed in `STAGING_PRODUCTION_STRATEGY.md`.

---

## 6. Explicit Stage 2 Exit Decision

### **Decision: PASS (CONDITIONAL ON OWNER CREDENTIAL ROTATION)**

**Rationale**:
- High-risk execution paths (`eval()`, environment template leakage) have been completely eliminated.
- Unauthenticated open routes (`/test-send`, `/transcribe`, `/parse-intent`, `/followup/questions`) are securely contained.
- SSRF defenses have been tested and verified across all standard attack vectors.
- A fully reproducible test environment targeting Python 3.11.16 has been established with **100 passing tests and 0 failures**.
- Remaining audit gaps (Google Sheets stubs, Google Drive fake fallbacks, HubSpot token refresh) are thoroughly documented for resolution in Stage 3.
- No Temporal implementation has been initiated prematurely.

**Stage 3 (Temporal & Resilient Engine Implementation) may begin upon owner review and credential rotation.**
