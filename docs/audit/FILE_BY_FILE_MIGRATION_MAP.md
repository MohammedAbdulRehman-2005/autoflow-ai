# File-by-File Migration Map (Stage 2 — Security Containment & Verification)

Companion to [`PRODUCTION_READINESS_AUDIT.md`](./PRODUCTION_READINESS_AUDIT.md), [`STAGE_2_SECURITY_CONTAINMENT.md`](./STAGE_2_SECURITY_CONTAINMENT.md), [`STAGING_PRODUCTION_STRATEGY.md`](./STAGING_PRODUCTION_STRATEGY.md), and [`STAGE_2_VERIFICATION_REPORT.md`](./STAGE_2_VERIFICATION_REPORT.md).

Status vocabulary:
- **STAGE 2 CONTAINED / VERIFIED**: High-risk vulnerability or blocker mitigated, protected by automated regression test in `test_stage2_security.py` or full test suite (100 passed).
- **VERIFIED WORKING**: Functionality verified working via automated test suite.
- **PARTIALLY IMPLEMENTED**: Code exists and handles partial flow; requires architectural refactor in Stage 3/4.
- **IMPLEMENTED BUT UNTESTED**: Code exists but lacks complete integration/e2e test coverage.
- **MOCK / PLACEHOLDER**: Stubbed implementations, fake return values, or unreachable dead code.
- **NOT IMPLEMENTED**: Feature declared or desired but entirely absent in codebase.
- **BROKEN**: Runtime failure or critical bug blocking execution.
- **REMOVED / CONTAINED**: Unsafe file deleted or route permanently disabled (410 Gone).

"Evidence" column: **R** = read in full/substantially, **G** = grep/enumeration only, **T** = verified via automated pytest suite.

---

## Backend — Core, Auth, Config

| Existing File/Module | Current Responsibility | Actual Implementation Status | Evidence | Keep / Refactor / Replace / Remove | Recommended Action / Stage 2 Status |
|---|---|---|---|---|---|
| `backend/main.py` | App factory, lifespan, CORS, error handlers, `/health` | **STAGE 2 CONTAINED / VERIFIED** | R, T. Origin reflection removed; origin regex restricted to verified Vercel & localhost domains; startup DDL still present (L66-77). | Refactor (Stage 3) | Startup DDL to Alembic; split lifespan from scheduler; replace APScheduler with Temporal worker. |
| `backend/core/config.py` | pydantic-settings | **STAGE 2 CONTAINED / VERIFIED** | R, T. Production fail-fast validator added (blocks default/weak JWT secrets & missing keys); `FERNET_KEY`/`ENCRYPTION_KEY` aliased; `UNSAFE_EVAL_ENABLED=False`; `ALLOW_INSECURE_HTTP=False`. | Keep / Extend | Add Temporal & LangGraph configuration blocks in Stage 3. |
| `backend/core/redis.py` | Redis pool | NEEDS VERIFICATION | G only. | Refactor (Stage 3) | Keep only for transient coordination/cache; move refresh tokens to Postgres. |
| `backend/core/rate_limit.py` | slowapi limiter keyed by remote address | PARTIALLY IMPLEMENTED | R, T. Keyed by remote address; now attached to transcribe (10/min), parse-intent (20/min), followup (30/min). | Refactor (Stage 3) | Add trusted-proxy IP resolution and user-id-based quota tiering. |
| `backend/auth/utils.py` | bcrypt + JWT helpers | VERIFIED WORKING | R, T. Tested in `test_sprint1.py` and `test_stage2_security.py`. | Keep | Add `iss`/`aud`, token rotation (`kid`), key management. |
| `backend/auth/service.py` | signup/login/refresh/logout, Redis jti store | **STAGE 2 CONTAINED / VERIFIED** | R, T. Converted Redis outage behavior to fail closed (`ValueError`). | Refactor (Stage 3) | Persist refresh sessions in Postgres; email verification; password reset; lockout; constant-time login. |
| `backend/auth/dependencies.py` | `get_current_user` | VERIFIED WORKING | R, T. Enforces valid token & active user; now applied to all previously exposed endpoints. | Refactor (Stage 3) | Add workspace/role resolution; central authorization dependency. |
| `backend/auth/router.py`, `schemas.py` | Auth endpoints/DTOs | VERIFIED WORKING | R, T. Tested in `test_sprint1.py`. | Keep | Add email verification/reset endpoints; MFA support. |

---

## Backend — Database

| Existing File/Module | Current Responsibility | Actual Implementation Status | Evidence | Keep / Refactor / Replace / Remove | Recommended Action |
|---|---|---|---|---|---|
| `backend/database/models.py` | 11 ORM models | PARTIALLY IMPLEMENTED | R. No workflow versions; `WorkflowRun` lacks version FK/`celery_task_id`; `ExecutionEvent` lacks FK; integration unique constraint mismatch. | Refactor (Stage 3) | Add `workflow_versions`, `runs.workflow_version_id`, idempotency keys, approvals, workspaces; reconcile enums; make runs projections of Temporal history. |
| `backend/database/schema.sql` | Hand-maintained DDL | PARTIALLY IMPLEMENTED (drifted) | G. Missing `execution_events`; enum values patched in `main.py`. | Replace (Stage 3) | Replace with Alembic baseline migration generated from the live DB schema. |
| `backend/database/session.py` | Engine/session factory | VERIFIED WORKING | R, T. Pool 10+20 per process, `pre_ping=True`. Verified via SQLite in test baseline. | Keep | Tune pool per deployment; add statement timeouts. |
| `backend/database/__init__.py` | Re-exports | VERIFIED WORKING | G, T. | Keep | — |

---

## Backend — Workflow Definition, Planning, Validation

| Existing File/Module | Current Responsibility | Actual Implementation Status | Evidence | Keep / Refactor / Replace / Remove | Recommended Action |
|---|---|---|---|---|---|
| `workflow/dsl/schema.py` | Pydantic DSL v1 | VERIFIED WORKING | R, T. Strong structural checks; redundant routing (`on_success`/`on_failure` + `edges`); tested in `test_sprint2.py`. | Refactor (Stage 3) | Seed for DSL v2: single routing representation, typed conditions/expressions, per-capability param models. |
| `workflow/dsl/validator.py`, `examples.py` | Graph validation, few-shot examples | VERIFIED WORKING | G, T. Verified in unit tests. | Refactor (Stage 3) | Fold into unified validation pipeline; reuse examples as planner/eval seeds. |
| `workflow/validator/**` (+ `validation_pipeline.py`) | 7 check modules, API router | PARTIALLY IMPLEMENTED | G, R, T. Template check whitelisted `env`; credential warnings. | Refactor (Stage 3) | Remove `env` whitelist; convert missing credentials to hard errors; unify with `dsl/validator.py`. |
| `workflow/capability_registry.py`, `node_registry.py` | Planner/UI metadata, capability patterns | **STAGE 2 CONTAINED / VERIFIED** | G, T. Added missing `doc_url` to `google_calendar.create_event` and `google_calendar.list_events`. | Keep → extend | Becomes static capability registry; add sensitivity, idempotency, side-effect class, egress policy. |
| `workflow/planner/service.py` | Groq planner, retry, persistence | IMPLEMENTED BUT UNTESTED | R. Retry/validation present; sends full DSL to LLM; no prompt versioning. | Refactor (Stage 3) | Re-home as LangGraph plan→clarify→generate→validate; model-agnostic client; prompt versions; redaction. |
| `workflow/planner/prompt.py` | System prompt builder | IMPLEMENTED BUT UNTESTED | G. Tells model to use `{{env.VAR}}` for sensitive values. | Refactor (Stage 3) | Remove env guidance; reference named credentials/secrets only. |
| `workflow/planner/editor_engine.py`, `editor_service.py`, `router.py`, `schemas.py` | Incremental edit, add-step, capabilities | VERIFIED WORKING | G, T. Tested in `test_sprint3.py`. | Refactor (Stage 3) | Route all mutations through single validated write path. |
| `workflow/crud/router.py` | Workflow CRUD | PARTIALLY IMPLEMENTED / **unsafe** | R. `POST /api/v1/workflows` accepts arbitrary JSON dicts without running `WorkflowDSL` validation. | Refactor (Stage 3) | Validate DSL + business rules at write; create immutable versions; enum status; transactional authz. |
| `workflow/validator/router.py` | Validation API | VERIFIED WORKING | G, T. | Keep | — |

---

## Backend — Execution Engine

| Existing File/Module | Current Responsibility | Actual Implementation Status | Evidence | Keep / Refactor / Replace / Remove | Recommended Action / Stage 2 Status |
|---|---|---|---|---|---|
| `workflow/engine/runner.py` | In-process sequential interpreter | PARTIALLY IMPLEMENTED | R, T. Sequential cursor; loop swallows errors; best-effort persistence; ignores timeouts/policies. | **Replace (Stage 3)** | Replace with deterministic Temporal workflow interpreting immutable DSL; keep as test oracle. |
| `workflow/engine/context.py` | Template resolution, run context | **STAGE 2 CONTAINED / VERIFIED** | R, T. Severed `os.environ` (`env: {}`); upgraded to `SandboxedEnvironment`; set `StrictUndefined`; explicit `TemplateResolutionError`. | Refactor (Stage 3) | Migrate to explicit reference/expression resolver with scoped credential vault. |
| `workflow/engine/credential_resolver.py` | Per-run credential lookup | PARTIALLY IMPLEMENTED | R. Direct DB queries; swallows decrypt errors; google suite mapping omits drive row. | Refactor (Stage 3) | Make it the only path; return typed errors; refresh/rotate through `TokenManager`; Activity-scoped. |
| `workflow/engine/registry.py` | `service.operation` → executor | PARTIALLY IMPLEMENTED | R. 35 keys; `create_draft`→send; `openai.*` → Groq; generic Drive fallback. | Refactor (Stage 3) | Fix mappings; 1 Activity per capability; remove misleading aliases. |
| `workflow/engine/router.py` | Run/list/get/node-types/execute-step | PARTIALLY IMPLEMENTED | R. BackgroundTasks execution; no idempotency key; no cancel route; `execute-step` bypasses runner. | Refactor (Stage 3) | Keep API shape; start Temporal workflow with idempotency key; add cancel/approve routes. |
| `workflow/engine/schemas.py` | Run DTOs | VERIFIED WORKING | G, T. Step-log DTO omits I/O. | Keep → extend | Add run timeline, approvals, version info. |
| `executors/base.py` | `BaseExecutor`/`ExecutorResult` | VERIFIED WORKING | G, T. | Refactor (Stage 3) | Add typed error taxonomy (retryable/terminal/credential), idempotency key param. |
| `executors/builtin.py` | condition/loop/wait/map/filter/set_var/trigger | **STAGE 2 CONTAINED / VERIFIED** | R, T. Python `eval()` completely eradicated; restricted AST evaluator (`evaluate_safe_condition`) implemented; feature flag `UNSAFE_EVAL_ENABLED=False`. | Refactor (Stage 3) | Wait → Temporal timer; condition AST preserved; loop/map/filter become pure workflow tasks. |
| `executors/http.py` | Generic HTTP request | **STAGE 2 CONTAINED / VERIFIED** | R, T. Enforces HTTPS scheme; blocks loopback, private RFC1918, link-local, cloud metadata IPs; disables redirects; caps response body at 5MB; strips sensitive headers. | Refactor (Stage 3) | Add domain allowlist per workspace; support mutual TLS if required. |
| `executors/ai_agent.py` | Groq generate/classify/extract | VERIFIED WORKING | R, T. Tested in `test_sprint3.py`. Groq only; binary confidence; swallowed JSON errors. | Refactor (Stage 3) | Provider abstraction (Gemini/Anthropic/Groq), structured output schemas, budget caps. |
| `executors/gmail.py` | Gmail list/send | PARTIALLY IMPLEMENTED | R, T. In-memory token refresh succeeds but does not persist new refresh token to DB; tokens in URL info. | Refactor (Stage 3) | Activity + idempotency (client msg-id/`References`), token manager, no tokens in URLs. |
| `executors/google_calendar.py` | Calendar events | VERIFIED WORKING | G, T. Tested in `test_sprint2.py`. Added missing `doc_url`. | Refactor (Stage 3) | Activity-scoped token refresh + contract tests. |
| `executors/google_drive.py` | Drive operations | **MOCK / PLACEHOLDER (on error)** | R. Generates fake `drive_folder_<uuid>` and returns `ok` on credential failure. | Refactor (Stage 3) | Eliminate fake success fallback; return typed terminal error. |
| `executors/google_sheets.py` | Sheets operations | **MOCK / PLACEHOLDER** | R. Stubs with commented-out Google Sheets v4 API calls; returns fake empty rows/objects. | Refactor (Stage 3) | Implement genuine Google Sheets API client with token manager. |
| `executors/hubspot.py` | HubSpot CRM | PARTIALLY IMPLEMENTED | R. Tokens expire in 30 minutes; no refresh logic; fails all subsequent executions. | Refactor (Stage 3) | Add OAuth refresh cycle; handle 429 rate limits. |
| `executors/slack.py`, `notion.py` | Slack & Notion integrations | IMPLEMENTED BUT UNTESTED | G, R. Own DB lookups; lacks rate-limit backoff. | Refactor (Stage 3) | Unify credential access; rate-limit aware retries; idempotency. |
| `workflow/event_bus.py`, `observability.py` | In-process pub/sub; local timing | MOCK / PLACEHOLDER | G. In-process only; lost on worker crash. | Replace (Stage 3) | OpenTelemetry + structured JSON logs; domain events via Temporal history. |
| `workflow/langgraph_engine/*` | LangGraph runtime, nodes, tools | MOCK / PLACEHOLDER (unreachable) | R, G. Tools simulate success; no `user_id`. | **Remove (Stage 3)** | Delete dead runtime; rebuild intelligent diagnosis & recovery in Stage 4. |

---

## Backend — Scheduling, Workers, Integrations, Routes

| Existing File/Module | Current Responsibility | Actual Implementation Status | Evidence | Keep / Refactor / Replace / Remove | Recommended Action / Stage 2 Status |
|---|---|---|---|---|---|
| `scheduler/service.py` | APScheduler wrapper | PARTIALLY IMPLEMENTED | R. In-process per replica on shared job store; race conditions on scale-out. | **Replace (Stage 3)** | Replace with Temporal Schedules (single leader, deduplicated, resilient). |
| `scheduler/jobs.py` | Cron entrypoint | **BROKEN** (no `user_id`) | R. Calls `WorkflowRunner(...)` without `user_id`/`workflow_id`. | Replace (Stage 3) | Folded into Temporal schedule → workflow start with owner identity. |
| `scheduler/router.py`, `schemas.py` | Schedule API | VERIFIED WORKING | G, T. Tested in `test_sprint3.py`. | Refactor (Stage 3) | Keep API shape; back with Temporal Schedules. |
| `workers/celery_app.py`, `tasks.py` | Celery app & tasks | MOCK / PLACEHOLDER (no producer) | R. `run_workflow_task` only enqueued by unused helper; no beat entries. | **Remove (Stage 3)** | Delete with Flower/RedBeat; do not migrate. |
| `workers/router.py` | Run status via Celery | BROKEN (unmounted) | R. Not included in `main.py`. | **Remove (Stage 3)** | Delete dead code. |
| `integrations/service.py` | OAuth URLs/exchange, Fernet crypto, upsert | **STAGE 2 CONTAINED / VERIFIED** | R, T. Implemented cryptographic 256-bit single-use OAuth state verification (`verify_and_consume_oauth_state`); Fernet/Encryption key aliases. | Refactor (Stage 3) | Centralized token manager with automated refresh and encrypted DB storage. |
| `integrations/router.py` | OAuth endpoints | **STAGE 2 CONTAINED / VERIFIED** | R, T. Bearer token prioritized via `Authorization` header; query string token transmission deprecated. | Refactor (Stage 3) | POST start flow with PKCE; sanitize provider error responses. |
| `integrations/context_fetcher.py` | Slack channel context for planner | IMPLEMENTED BUT UNTESTED | G. | Refactor (Stage 3) | Treat output as untrusted prompt input; cache. |
| `intent_parser/service.py` | Keyword intent | MOCK / PLACEHOLDER | R. 5 keywords + constant confidence. | Replace (Stage 4) | Replace with LLM/graph clarification step. |
| `intent_parser/router.py` | Natural language intent parsing | **STAGE 2 CONTAINED / VERIFIED** | R, T. Protected by `get_current_user` auth; rate limited (20/min). | Refactor (Stage 4) | Fold into planner clarification graph. |
| `intent_parser/gemini_followup.py` | Gemini follow-up question generator | **STAGE 2 CONTAINED / VERIFIED** | R, T. Lazy client initialization (`_get_client()`); resolved import-time crash. | Refactor (Stage 4) | Fold into planner clarification graph. |
| `followup_engine/router.py` | Follow-up question engine | **STAGE 2 CONTAINED / VERIFIED** | R, T. Protected by `get_current_user` auth; rate limited (30/min). | Refactor (Stage 4) | Fold into planner clarification graph. |
| `gmail/router.py` | Gmail test router | **STAGE 2 CONTAINED / VERIFIED** | R, T. Disabled `/api/v1/gmail/test-send` (permanently returns HTTP 410 Gone). | **Remove (Stage 3)** | Delete router entirely. |
| `routes/transcribe.py` | Audio transcription router | **STAGE 2 CONTAINED / VERIFIED** | R, T. Protected by `get_current_user` auth; rate limited (10/min). | Refactor (Stage 4) | Stream to temp with strict magic-byte validation and user storage quotas. |
| `services/whisper_service.py` | Whisper audio service | IMPLEMENTED BUT UNTESTED | R. | Keep | Add audio file sanitization. |
| `patch_slack_channel.py` | One-off DB patch | NOT APPLICABLE | G. | Remove (Stage 3) | Delete. |

---

## Backend — Tests

| Existing File/Module | Current Responsibility | Actual Implementation Status | Evidence | Keep / Refactor / Replace / Remove | Recommended Action / Stage 2 Status |
|---|---|---|---|---|---|
| `backend/tests/conftest.py` | Test fixtures | VERIFIED WORKING | R, T. SQLite in-memory / file fixture; mocked Redis; mock Sentry SDK. | Keep / Extend | Add Temporal test workflow environment fixtures in Stage 3. |
| `backend/tests/test_health.py` | Health smoke | VERIFIED WORKING | R, T. Passes cleanly in 3.11 test suite. | Keep | Add DB and Redis readiness assertions. |
| `backend/tests/test_sprint1.py` | Auth & DB unit tests | VERIFIED WORKING | R, T. 20 passed tests in 3.11 test suite. | Keep / Refactor | Re-organize by domain. |
| `backend/tests/test_sprint2.py` | Node registry & DSL tests | VERIFIED WORKING | R, T. 33 passed tests in 3.11 test suite. | Keep / Refactor | Re-organize by domain. |
| `backend/tests/test_sprint3.py` | Editor & planner tests | VERIFIED WORKING | R, T. 27 passed tests in 3.11 test suite. | Keep / Refactor | Re-organize by domain. |
| `backend/tests/test_stage2_security.py` | **Stage 2 Security Regression Suite** | **VERIFIED WORKING (NEW)** | R, T. 20 passed security regression tests covering template injection, safe AST evaluation, SSRF protection, unauthenticated endpoint lockdown, OAuth state validation, and fail-fast configuration. | **Keep (Permanent)** | Protects security baseline across all future stages. |

---

## Frontend

| Existing File/Module | Current Responsibility | Actual Implementation Status | Evidence | Keep / Refactor / Replace / Remove | Recommended Action / Stage 2 Status |
|---|---|---|---|---|---|
| `frontend/src/pages/WorkflowBuilderPage.jsx` | Canvas, planner UI, save, run | **STAGE 2 CONTAINED / VERIFIED** | R, G, Build. Injected Bearer authentication into transcribe and parse-intent client requests; `npm run build` passes cleanly. | Refactor (Stage 4) | Split 913-line component; migrate from `localStorage` drafts to server-authoritative state. |
| `frontend/src/components/*` | Canvas & inspector UI components | VERIFIED WORKING (Build) | G, Build. Built successfully in Vite. | Keep / Refactor | Align with DSL v2 schemas. |
| `frontend/src/services/apiClient.js`, `authApi.js` | HTTP client & auth | IMPLEMENTED BUT UNTESTED | R. Access token in memory, refresh in `localStorage`. | Refactor (Stage 3) | Move refresh token to HttpOnly cookie; single-flight refresh mutex. |
| `frontend/src/mockData.js` | Local fixtures | MOCK / PLACEHOLDER | G. Used in `MarketplacePage.jsx`. | Remove (Stage 4) | Replace with real API templates. |

---

## Root / Ops / Audit Documentation

| Existing File/Module | Current Responsibility | Actual Implementation Status | Evidence | Keep / Refactor / Replace / Remove | Recommended Action / Stage 2 Status |
|---|---|---|---|---|---|
| `query_db.py` | Ad-hoc DB query script | **REMOVED (CONTAINED)** | Deleted from working tree; added to `.gitignore`. | **Deleted** | Secret rotation checklist provided; git history rewrite pending owner rotation. |
| `check_hash.py` | bcrypt check script | **REMOVED (CONTAINED)** | Deleted from working tree; added to `.gitignore`. | **Deleted** | Secret rotation checklist provided; git history rewrite pending owner rotation. |
| `extract_url.py` | URL probe script | **REMOVED (CONTAINED)** | Deleted from working tree; added to `.gitignore`. | **Deleted** | Cleaned up. |
| `docs/audit/PRODUCTION_READINESS_AUDIT.md` | Comprehensive Stage 1 Audit | VERIFIED COMPLETE | R. 60KB authoritative audit report. | Keep | Authoritative Stage 1 baseline. |
| `docs/audit/TEST_BASELINE.md` | Stage 1 Test Baseline Record | VERIFIED COMPLETE | R. Documents original state and blockers. | Keep | Baseline history. |
| `docs/audit/STAGE_2_SECURITY_CONTAINMENT.md` | **Stage 2 Security Report** | **VERIFIED COMPLETE (NEW)** | R. Detailed record of all 5 security workstreams and remediations. | **Keep** | Authoritative Stage 2 containment document. |
| `docs/audit/STAGING_PRODUCTION_STRATEGY.md` | **Deployment Safety Strategy** | **VERIFIED COMPLETE (NEW)** | R. Zero-risk isolation strategy, environment boundaries, and CI/CD promotion gates. | **Keep** | Authoritative deployment specification. |
| `docs/audit/STAGE_2_VERIFICATION_REPORT.md` | **Stage 2 Verification Evidence** | **VERIFIED COMPLETE (NEW)** | R. Test logs, build logs, and regression suite verification. | **Keep** | Authoritative Stage 2 sign-off report. |
| `docker-compose.yml` | Development compose | BROKEN for production | R. Lacks DB init, exposed dev ports. | Replace (Stage 3) | Replace with production-grade Compose with Temporal & Postgres services. |
| `Dockerfile.backend` | Backend container | PARTIALLY IMPLEMENTED | R. Runs as root. | Refactor (Stage 3) | Multi-stage build, non-root user, healthcheck. |
