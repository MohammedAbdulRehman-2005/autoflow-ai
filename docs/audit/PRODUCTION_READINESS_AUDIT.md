# AutoFlow AI X — Production Readiness Audit (Stage 1)

- **Audit date:** 2026-11-01
- **Repository:** `MohammedAbdulRehman-2005/autoflow-ai` (local checkout `d:\autoflow-ai`, 175 commits, HEAD `a94feaf`)
- **Method:** Static code reading plus one attempted test run. **No application code was modified, no dependency was installed, and no exploit was executed.** Every "exploitable" claim below is derived from reading code, not from a live attack.
- **Companion documents:** [`FILE_BY_FILE_MIGRATION_MAP.md`](./FILE_BY_FILE_MIGRATION_MAP.md), [`TEST_BASELINE.md`](./TEST_BASELINE.md)

**Status legend:** VERIFIED WORKING · PARTIALLY IMPLEMENTED · IMPLEMENTED BUT UNTESTED · MOCK / PLACEHOLDER · NOT IMPLEMENTED · BROKEN · NEEDS VERIFICATION · NOT APPLICABLE
**Priority legend:** P0 fix before any public deployment · P1 before production release · P2 important reliability/maintainability · P3 later
> No path was marked VERIFIED WORKING, because the test suite could not be run (see §11) and I did not run the application. Items are marked "IMPLEMENTED BUT UNTESTED" where the code path looks complete.

Line numbers refer to the files as read on 2026-11-01 (CRLF line endings).

---

## 1. Executive Summary

**What it is.** A FastAPI + React/React-Flow application. A user describes an automation in natural language. The Groq `llama-3.3-70b-versatile` model generates a JSON workflow DSL, which is validated with Pydantic plus custom graph/schema checks and stored as JSONB in `workflows.ai_context_json`. A single-process, in-memory interpreter (`WorkflowRunner`) executes the graph node by node. Runs are started from `BackgroundTasks` (manual) or APScheduler (cron). Eight integrations have executor code (Gmail, Sheets, Calendar, Drive, Slack, Notion, HubSpot, HTTP) plus Groq LLM nodes.

**Verdict: Prototype.** It is a demo-grade product that deploys to Render/Vercel/Supabase. It is **not** a Functional MVP by the standard you set, because:

1. **Critical security flaw (P0).** Any self-registered user can very likely read all server environment variables (JWT secret, DB URL, Fernet key, API keys) and run arbitrary Python on the API host, via the "Execute Step" endpoint. Two independent routes exist: the non-sandboxed Jinja environment (`context.py:45`) and `eval()` in the condition executor (`builtin.py:58`). Signup is open with no email verification.
2. **A production Supabase connection string is committed to git** (`query_db.py:3`), alongside a bcrypt hash and candidate plaintext (`check_hash.py:2`). Treat both as compromised.
3. **Execution is not durable.** Runs live inside the API process (`BackgroundTasks`). A restart leaves runs stuck in `pending`/`running` forever. Nothing resumes or reaps them.
4. **Scheduled runs cannot use integrations.** `execute_scheduled_workflow` builds `WorkflowRunner` without `user_id`/`workflow_id` (`scheduler/jobs.py:89-94`), so credentials are never resolved. Any scheduled Gmail/Slack/etc. node fails.
5. **The Celery/LangGraph subsystem is dead code from the API.** Nothing dispatches `run_workflow_task`, the workers router is never mounted, and the LangGraph "tools" return simulated success.
6. **There are no real tests of the execution path.** 81 tests exist. They are DTO, registry and validator unit tests. None could run in the available environment (§11).
7. **Reproducibility is poor.** There are no migrations (hand-maintained `schema.sql` plus startup `ALTER TYPE`). `docker-compose.yml` never initialises the DB and omits required env vars. `.env.example` and the README are incomplete or stale.

**What does appear sound** (by reading, not by running): bcrypt password hashing, short-lived access JWT with typed claims, refresh-token rotation (when Redis is up), ownership filters on every workflow/run query, Fernet encryption of integration credentials at rest, Pydantic DSL with enum-restricted services/operations, planner retry loop with validation feedback, and an LLM-bounded loop/visit safety limit.

**Reuse potential is real.** The DSL schema, node registry/capability registry, validator checks, planner prompt/retry structure, editor/mutation concepts, and the frontend canvas are good raw material for the target architecture. The runtime, scheduling, auth hardening, credential handling and persistence model need replacement.

---

## 2. Repository Structure

Observed from `git ls-files` (≈14k lines excluding lockfiles and docs):

| Path | Contents | Notes |
|---|---|---|
| `backend/main.py` | FastAPI app, lifespan, CORS, health | enum `ALTER TYPE` at startup (L66-77) |
| `backend/auth/` | signup/login/refresh/logout, JWT, bcrypt, Redis refresh store | |
| `backend/core/` | `config.py` (pydantic-settings), `redis.py`, `rate_limit.py` (slowapi) | |
| `backend/database/` | `models.py` (SQLAlchemy 2.0), `schema.sql`, `session.py` | **no Alembic/migrations dir** |
| `backend/workflow/dsl/` | Pydantic DSL (`schema.py`), `validator.py`, `examples.py` | |
| `backend/workflow/planner/` | LLM planner (Groq), prompt, editor engine/service, router | |
| `backend/workflow/validator/` + `validation_pipeline.py` | 7 check modules | |
| `backend/workflow/engine/` | `runner.py`, `context.py`, `credential_resolver.py`, `registry.py`, `executors/*`, `router.py` | core runtime |
| `backend/workflow/langgraph_engine/` | graph builder, nodes, runtime, tools | reachable only from Celery |
| `backend/workflow/node_registry.py`, `capability_registry.py` | metadata registries (UI + planner) | |
| `backend/scheduler/` | APScheduler service/jobs/router | |
| `backend/workers/` | Celery app, tasks, run-status router | router not mounted |
| `backend/integrations/` | OAuth flows, Fernet crypto, router, context fetcher | |
| `backend/intent_parser/`, `followup_engine/` | keyword intent parsing + Gemini follow-up questions | unauthenticated |
| `backend/gmail/` | Resend "test email" endpoint | unauthenticated |
| `backend/routes/transcribe.py`, `services/whisper_service.py` | audio transcription | unauthenticated |
| `backend/patch_slack_channel.py` | one-off DB patch script | |
| `backend/tests/` | `test_health.py`, `test_sprint{1,2,3}.py`, `conftest.py` | 81 tests |
| `frontend/` | React 19, Vite 8, `@xyflow/react`, Tailwind 4, no test runner | |
| `docs/`, `Architecture.md`, `implementation_plan.md`, `IMPLEMENTATION_PROMPTS.md` | extensive design docs | partially aspirational (§12) |
| Root: `query_db.py`, `check_hash.py`, `extract_url.py` | debug scripts | **contain secrets** (§7) |
| `Dockerfile.backend`, `Dockerfile.frontend`, `docker-compose.yml`, `.env.example` | deploy | |

**Not found:** `.github/` (no CI), Alembic/migrations, `pytest.ini`/`pyproject.toml`, webhook route, cancel endpoint, RBAC, org/tenant tables, Dockerfile healthchecks, frontend tests.

---

## 3. Existing Architecture

```
React/Vite SPA (Vercel)  ──HTTPS──▶  FastAPI (Render)
                                      ├─ /auth, /workflows(CRUD), /ai/plan-workflow, /workflows/{id}/run
                                      ├─ APScheduler (in-process, SQLAlchemyJobStore → Postgres)
                                      ├─ BackgroundTasks → WorkflowRunner (in-process asyncio)
                                      ├─ Redis (refresh-token jti store, slowapi)
                                      └─ Postgres/Supabase (SQLAlchemy ORM, JSONB DSL)
Celery worker/beat/flower (docker-compose only) ── no producer ── LangGraph runtime
LLMs: Groq (planner, LLM nodes, LangGraph), Gemini (follow-up questions), Groq/OpenAI Whisper (transcribe)
```

Key design facts, all verified from code:
- The **DSL stored in `workflows.ai_context_json` is the source of truth**. `workflow_nodes`/`workflow_edges` rows are a denormalised mirror used only to attach step logs (`runner.py:541-600`).
- There is **one runtime that is actually reachable**: `WorkflowRunner` (single cursor, `on_success`/`on_failure` pointers).
- Security rests on user-ownership filters (`Workflow.user_id == current_user.id`). There is no tenant/org concept and no roles.

---

## 4. Actual End-to-End Execution Lifecycle

Answers to the twelve required questions, with evidence.

| # | Question | Answer (observed) | Evidence |
|---|---|---|---|
| 1 | Frontend → backend | SPA calls `POST /api/v1/ai/parse-intent` (unauthenticated), `POST /api/v1/ai/plan-workflow` (auth), saves/edits via `POST/PATCH /api/v1/workflows`, runs via `POST /api/v1/workflows/{id}/run`. Base URL from `VITE_API_URL`, default `http://localhost:8000`. Access token in memory, refresh token in `localStorage`. | `main.py:172-182`; `frontend/src/services/apiClient.js:10-18`; `intent_parser/router.py`; `workflow/planner/router.py` |
| 2 | How DSL is generated | `plan_workflow()` builds a prompt, calls Groq in JSON mode, `_extract_json`, `json.loads`, `WorkflowDSL.model_validate`. Alternatively the editor builds DSL deltas from the capability/node registries without an LLM; the user can also post DSL directly to `POST /workflows`. | `planner/service.py:232-415` (`plan_workflow`, `_call_groq`, `_extract_json`); `crud/router.py:137-157` |
| 3 | How DSL is validated | **Planner path:** Pydantic (`WorkflowDSL` validators: unknown edge refs, exactly 1 trigger, unique IDs, enum service/operation) + `validate_workflow_graph` + `check_schema`. Retried up to `MAX_RETRIES=2` with feedback. **CRUD path (`POST`/`PATCH /workflows`): NO validation at all** – raw `dict` stored. **Run path:** `WorkflowDSL.model_validate` + `WorkflowValidator.validate` gate before `trigger_run`. | `planner/service.py:351-381`; `crud/router.py:62-71,148,182`; `engine/router.py:143-165` |
| 4 | How execution begins | `trigger_run` creates a `WorkflowRun(status=pending)`, commits, then `background_tasks.add_task(_run_workflow_background, …)`. The background task opens a new `SessionLocal()` and calls `WorkflowRunner.run()`. Cron path: APScheduler → `execute_scheduled_workflow` → `WorkflowRunner.run()`. | `engine/router.py:67-101,168-192`; `scheduler/jobs.py:18-105` |
| 5 | How nodes execute | `_execute_from_node` loops on a single cursor. `_execute_with_retry` resolves params once, resolves credentials, then `_dispatch_executor` → `get_executor("service.operation")` → `executor.execute(node, context, params)`. | `runner.py:221-272,347-471`; `registry.py:73-148` |
| 6 | Output passing | `context.set_node_output(node.id, result.output)` on success. Templates `{{node_id.output.field}}` resolve through Jinja against a flat dict. | `runner.py:396-399`; `context.py:140-198` |
| 7 | Node failure | Up to `max_attempts` (default **3**, 30 s base, ×2) for **every** node regardless of idempotency or error class. Then `on_failure` edge, or raise → run `failed`. `error_policy`, `timeout_seconds`, `execute_once`, `always_output_data` are **not read by the runner** (grep: only schema/tests/`execute_single_node` logging). | `runner.py:360-453,258-272`; `dsl/schema.py:241-272` |
| 8 | Resume after restart | **No.** `BackgroundTasks` runs die with the process; rows stay `pending`/`running`. No reaper, no lease, no checkpoint. Celery has `acks_late`, but no code path enqueues to it. The `execution_events` ledger is written but nothing reads it, and its table is not in `schema.sql`. | `engine/router.py:185`; `runner.py:477-500`; `database/schema.sql` (no `execution_events`) |
| 9 | Duplicate triggers → duplicate side effects | **Yes.** `POST /run` has no idempotency key. Executor retries re-send emails/messages. APScheduler runs in every API replica against a shared job store (unsupported by APScheduler) while Celery Beat is a separate scheduler. No executor uses idempotency keys (grep: none). | `engine/router.py:108-192`; `scheduler/service.py:74-101`; `runner.py:374-439` |
| 10 | Reliable persistence of state | **No.** Status/step-log writes are best-effort: failures are logged and swallowed (`runner.py:534-539,595-600`), and node outputs live only in process memory. `WorkflowRun.context_snapshot` is only written by the unreachable LangGraph path; `ExecutionContext.snapshot()` is never persisted by `WorkflowRunner`. | `runner.py:502-600`; `context.py:233-244` |
| 11 | Can a workflow change mid-run? | The in-flight in-process run holds the parsed DSL object, so it is isolated. But: no immutable version exists; `WorkflowRun` has no `workflow_version`/DSL snapshot column; `PATCH` overwrites in place and just `version += 1`. The Celery path re-reads the DSL from DB on every retry, so edits could be picked up mid-retry. No run can be traced back to the exact DSL it executed. | `crud/router.py:181-184`; `models.py:344-406`; `tasks.py:80-88` |
| 12 | Parallel/conditional workflows | **Conditional: PARTIALLY IMPLEMENTED** (`_resolve_condition_next` matches edge label true/false/yes/no, falls back to `on_success`/`on_failure`). **Parallel: NOT IMPLEMENTED** – a non-condition node follows exactly one `on_success` pointer; `WorkflowEdgeDSL.condition` is never evaluated; there is no fan-out/join. **Loops: PARTIALLY** – body runs sequentially; nothing after the loop body ever runs (`current_id=None`, `runner.py:251`); body exceptions are swallowed and the run still reports success (`runner.py:334-335`); lists >500 are silently truncated (`runner.py:312-317`). | `runner.py:245-253,274-341` |

**Other lifecycle findings**
- **Template failure is silent.** `_render_string` returns the original template string on any exception (`context.py:224-227`) and `_SilentUndefined` renders missing variables as `""` (`context.py:35-41`). An email can be sent to an empty/literal-template field with no error.
- **No cancellation.** `RunStatus.cancelled` exists, but the engine router exposes 5 routes (run, list, get, node-types, execute-step) and none cancel a run; the runner checks no cancel flag.
- **Scheduled runs lose identity.** `jobs.py:89-94` constructs `WorkflowRunner(dsl, run_id, db, trigger_payload)` with no `user_id`, so `CredentialResolver` queries `Integration.user_id == None` and every integration node fails. It also does not check `workflow.status`.
- **Wait nodes block the interpreter** with `asyncio.sleep` up to 24 h (`builtin.py:122-126`) inside the API process.

---

## 5. Workflow Engine Audit

| Component | Status | Evidence / Finding |
|---|---|---|
| `WorkflowRunner` (`engine/runner.py`) | PARTIALLY IMPLEMENTED (sequential only) | Single-cursor DFS. MAX_NODE_VISITS=1000 and MAX_LOOP_ITERATIONS=500 guards (L47-48). Run-level status update after every node attempt = 2 commits per step. |
| `ExecutionContext` (`engine/context.py`) | BROKEN (security) | See §7 C-1/C-2. Docstring/comment claims "sandboxed" (L44) but uses plain `Environment` (L45). |
| `NodeRegistry` (`workflow/node_registry.py`) | IMPLEMENTED BUT UNTESTED (metadata only) | UI/validation metadata over the executor table; tests only check presence/shape (`test_sprint2.py:353-432`). |
| Executor registry (`engine/registry.py`) | PARTIALLY IMPLEMENTED | 35 keys. **No executor** for `twilio`, `whatsapp`, `airtable`, `salesforce` although `ServiceType` accepts them (`dsl/schema.py:44-76`; `stripe` is not in `ServiceType` at all). Such nodes pass DSL validation and fail at runtime (`runner.py:461-465`). `openai.*` nodes silently call **Groq** (`registry.py:103-105`, `ai_agent.py:57`). `gmail.create_draft` is mapped to the *send* executor (`registry.py:88`) → "create draft" sends a real email. |
| Dependency resolution | NOT IMPLEMENTED | No DAG/topological scheduling; the DSL pointers decide order. `validate_workflow_graph`/`checks/graph.py` check structure, not runtime semantics. |
| Conditional execution | PARTIALLY IMPLEMENTED | Condition value comes from `eval()` (§7 C-2). Edge `condition` field unused. |
| Parallel execution | NOT IMPLEMENTED | §4 Q12. |
| Loop handling | PARTIALLY IMPLEMENTED | §4 Q12. `{{item}}` implemented via `set_loop_item`. |
| State transitions | PARTIALLY IMPLEMENTED | `pending → running → retrying/success/failed`. No `cancelled`, `timed_out`, `waiting_approval`; `retrying` flips the whole run, not a node. Transitions are unguarded writes (no compare-and-set), so a late writer can overwrite a terminal state. |
| Cancellation | NOT IMPLEMENTED | |
| Error handling | PARTIALLY IMPLEMENTED | Retries are blind: HTTP 4xx, auth failures and validation errors are retried 3× with up to 30 s+60 s sleeps. |
| Retry | PARTIALLY IMPLEMENTED | Bounded (`RetryPolicy.max_attempts ≤ 10`) but no jitter, no error classification, no `Retry-After` handling (grep for `Retry-After`/`429`: only a test and `_classify_error`). |
| Execution persistence | PARTIALLY IMPLEMENTED | Step logs written best-effort; `input_json` stores resolved params (including any resolved secrets/headers). `StepLogSummary` does not expose input/output to the API (`engine/schemas.py`), so the UI cannot show node outputs either. |
| Workflow versioning | NOT IMPLEMENTED | Counter only (`Workflow.version`, `dsl.version`). No version table, no run→version FK. |
| Single-node "Execute Step" | IMPLEMENTED BUT UNTESTED; **dangerous** | Runs real executors with user-supplied `params_override` (`engine/router.py:396-509`, `runner.py:166-215`). Output scrub is shallow, top-level key-name only (`router.py:367-375`). |
| `LangGraphRuntime` | MOCK / PLACEHOLDER (unreachable) | Only imported by `workers/tasks.py:26`. Creates `WorkflowRunner` / graph **without `user_id`** (`runtime.py:85-92,100-106`). `tools.py:36-114`: `send_email_tool`, `send_sms_tool`, `append_sheet_tool` return simulated success and never call any API. |
| Event bus / `execution_events` | PARTIALLY IMPLEMENTED | In-process pub/sub (`event_bus.py`); DB ledger writes are swallowed at `DEBUG` (`runner.py:495-500`) and the table is absent from `schema.sql`. `Architecture.md` describes an event-sourced durable runtime that does not exist. |
| Observability (`workflow/observability.py`) | MOCK / PLACEHOLDER | Local timing spans; no OpenTelemetry/metrics. |

---

## 6. AI and LLM Audit

**Pipeline actually implemented**

```
NL prompt ─▶ /ai/parse-intent  (keyword matcher `parse_user_intent` + Gemini follow-up questions; UNAUTHENTICATED)
          ─▶ /ai/plan-workflow (Groq JSON-mode → Pydantic → graph + schema checks → retry ≤2 → DB save as draft)
          ─▶ editor endpoints  (capability registry + optional LLM edit)
```

| Question | Finding | Evidence |
|---|---|---|
| Providers integrated | **Groq** (planner, `groq.*`/`openai.*` LLM nodes, LangGraph nodes), **Gemini** (`generate_followup_questions`), **OpenAI/Groq Whisper** (transcribe). **OpenAI is not actually used for LLM nodes.** | `planner/service.py:26,213-225`; `executors/ai_agent.py:11,57`; `intent_parser/gemini_followup.py:7`; `services/whisper_service.py:16-17` |
| Structured responses | JSON mode (`response_format={"type":"json_object"}`), **not** schema-constrained; `_extract_json` has regex fallbacks. | `planner/service.py:218-225,61-82` |
| DSL validated | Yes on the planner path (Pydantic + graph + schema). Not on CRUD `POST/PATCH`. | §4 Q3 |
| Unsupported nodes rejected | Partially. Unknown services/operations are rejected by enums. Services without executors (twilio, whatsapp, airtable, salesforce) are *accepted* and fail at run time. | `dsl/schema.py:44-120`; `registry.py` |
| Clarification mechanism | Partial: `parse-intent` returns `need_clarification` + questions from Gemini. `parse_user_intent` is a 5-keyword matcher with a hard-coded `confidence: 0.8` (`intent_parser/service.py`) – a placeholder. The planner itself never asks the user questions. | `intent_parser/router.py`; `service.py` |
| Retry on malformed output | Yes: `MAX_RETRIES = 2` with the assistant output and validation errors fed back (`build_retry_prompt`). Broad `except` around API failures. | `planner/service.py:51,308-381` |
| Prompts versioned | **No.** No `PROMPT_VERSION` anywhere; prompts are f-strings in `planner/prompt.py`. | grep |
| LLM outputs tested | **No.** No test imports `plan_workflow`/`_call_groq`; test files only set a dummy `GROQ_API_KEY`. | grep of `backend/tests` |
| Eval dataset/benchmark | **None found.** `workflow/dsl/examples.py` holds few-shot examples, not an evaluation set. | |
| Sensitive data sent to LLM | The planner sends intent text, the **entire existing DSL** (`json.dumps(existing_dsl)`, `service.py:447`) on edits – any literal secret pasted into params goes to Groq – and live Slack channel names (`service.py:290-301`). LLM runtime nodes send resolved prompts (which may contain `{{env.*}}`-resolved values). No redaction layer. | `planner/service.py:285-301,440-449`; `executors/ai_agent.py` |
| Prompt-injection exposure | **High design risk.** Trigger/payload text flows straight into `llm_*` nodes whose output feeds downstream side-effect nodes (email, HTTP). No output validation, no tool allow-list, no human approval. The planner prompt itself instructs the model to *"Use `{{env.VAR}}` for all sensitive values"* (`planner/prompt.py:220`), and the template validator whitelists the `env` namespace (`validator/checks/templates.py:30`). A prompt-injected or malicious DSL can therefore request `{{env.DATABASE_URL}}`, etc. | cited |
| Dangerous parameter | `LLMGenerate` accepts `model` from params; `max_tokens` unbounded by policy → cost abuse. | `ai_agent.py:48-50` |

**Real vs placeholder:** Planner generation/validation/retry = real and reasonably built (IMPLEMENTED BUT UNTESTED). Intent parser = PLACEHOLDER. LangGraph agents/tools = MOCK. OpenAI nodes = MISLEADING alias to Groq.

---

## 7. Security Audit

Severity: Critical / High / Medium / Low / Informational. Priority in brackets.

### Verification of the previously identified `context.py` concerns

| Prior observation | Current code | Verdict |
|---|---|---|
| `_build_jinja_vars()` exposes all env vars via `env` | `context.py:166-167`: `"env": {k: v for k, v in os.environ.items()}` (the comment on L166 says "filtered" – it is not) | **CONFIRMED** |
| Jinja uses a normal `Environment`, not sandboxed | `context.py:44-51`: `Environment(loader=BaseLoader(), …)`; the comment on L44 says "sandboxed" – it is not (`jinja2.sandbox` is not imported) | **CONFIRMED** |
| `_SilentUndefined` silently converts missing vars to `""` | `context.py:35-41` (`__str__`→`""`, `__getattr__`/`__getitem__` return another `_SilentUndefined`); plus `_render_string` returns the raw template on any exception (L224-227) | **CONFIRMED** (and worse: swallowed errors) |

### Findings

| ID | Severity [Priority] | Finding | Evidence | Why it matters | Recommended action |
|---|---|---|---|---|---|
| **C-1** | **Critical [P0]** | **Server-side template injection → RCE and full env disclosure by any authenticated user.** Jinja is unsandboxed, and user-controlled strings are rendered. Reachable via `POST /workflows/{id}/nodes/{node_id}/execute` with `params_override` (user-supplied) and via any workflow params. | `context.py:45-51,200-227`; `engine/router.py:396-509`; `runner.py:207-210` | Standard Jinja SSTI (`__class__.__mro__…`) executes Python in the API process. | Replace with `SandboxedEnvironment` + `StrictUndefined`, or drop Jinja for a minimal explicit expression/reference language. Delete the `env` namespace. |
| **C-2** | **Critical [P0]** | **`eval()` in condition executor.** `eval(condition_raw, {"__builtins__": {}}, {})`, where `condition_raw` is a template-resolved string that can contain trigger/payload/LLM data. Empty `__builtins__` is a well-known non-boundary (object-graph traversal via `().__class__…`). | `executors/builtin.py:56-61` | Second independent RCE route. | Remove `eval`. Replace with a typed comparison AST from the DSL (op/left/right) evaluated deterministically. |
| **C-3** | **Critical [P0]** | **All environment variables readable from templates** (`JWT_SECRET_KEY`, `DATABASE_URL`, `ENCRYPTION_KEY`, `GROQ_API_KEY`, OAuth client secrets, `RESEND_API_KEY`, …). Exfiltration paths: Execute-Step response (`map_fields` output is `{"result": {...}}`, so the shallow `_scrub_secrets` at `router.py:367-375` does not catch nested values); any HTTP node (no egress limits); Slack/email nodes; LLM prompts; persisted `step_log.input_json`. The planner prompt and template validator actively *encourage* `{{env.*}}` (see §6). | `context.py:167`; `router.py:367-375,491`; `runner.py:388`; `planner/prompt.py:189,220`; `validator/checks/templates.py:30` | With the JWT secret an attacker mints tokens for any user; with `ENCRYPTION_KEY` they can decrypt every stored OAuth token. **Open signup + no email verification = unauthenticated-equivalent exposure.** | Remove `env`; pass an explicit per-workflow `secrets` namespace backed by a vault/credential table; redact on log/persist. |
| **C-4** | **Critical [P0]** | **Production database credentials committed to git** (`query_db.py:3`: full Supabase pooler URL with user/password/host) and a bcrypt hash + candidate plaintext (`check_hash.py:2`). They are in history (introduced in `916318b`). *Values intentionally not reproduced here.* | `query_db.py`, `check_hash.py` | Anyone with repo access (public repo?) owns the DB and all stored credentials/tokens. | Rotate the DB password and the referenced user's password now; purge history (`git filter-repo`) after rotation; delete the scripts; enable secret scanning. |
| **S-5** | **High [P0]** | **Unauthenticated, cost- and abuse-bearing endpoints**: `POST /api/v1/gmail/test-send?email=` (sends mail from the shared Resend key to *any* address → spam relay), `POST /api/v1/transcribe` (Groq/OpenAI spend, file upload), `POST /api/v1/ai/parse-intent` (Gemini), `POST /api/v1/followup/questions`. `/health` (leaks which provider keys exist) and `/api/v1/scheduler/status` are also public. | `gmail/router.py:9`; `routes/transcribe.py:23-24`; `intent_parser/router.py`; `followup_engine/router.py`; `main.py:194-230` | Direct financial loss, sender-reputation damage, DoS. | Require auth + per-user quotas; remove `test-send`; trim `/health` output. |
| **S-6** | **High [P0]** | **SSRF in the HTTP executor and unlimited egress.** Any user-supplied URL (incl. cloud metadata `169.254.169.254`, `localhost`, internal Postgres/Redis hosts) with caller-controlled headers/body; response headers and body are returned and stored. | `executors/http.py:42-85` | Internal network access from the app host. | Egress allow-list/deny private ranges, resolve-then-pin IPs, disable redirects, size/time caps, treat as "sensitive" capability requiring approval. |
| **S-7** | **High [P0/P1]** | **OAuth `state` is `"{user_id}:{provider}"`, unsigned and unbound to a session** → account-linking CSRF. An attacker can complete OAuth with their own provider account and have the callback attach those tokens to a victim's `user_id` (needs the victim's UUID). | `integrations/service.py:135,168`; `integrations/router.py:105-136` | Victim workflows act as the attacker's account (data exfiltration). | Random, single-use, server-stored `state` (+PKCE), bound to the session; verify on callback. |
| **S-8** | **High [P1]** | **Access JWT passed in the query string** for `GET /integrations/{provider}/connect?token=…` (→ web-server logs, browser history, Referer). | `integrations/router.py:52-97` | Token leakage; mitigated by 15-min TTL. | Start OAuth with an authenticated `POST` that returns the redirect URL, or use a short-lived one-time nonce. |
| **S-9** | **High [P1]** | **Insecure default secrets and no startup guard.** `JWT_SECRET_KEY` defaults to a public string (`config.py:41`); `docker-compose.yml:22` defaults to `change-me-in-production`; `FERNET_KEY` setting exists but is unused, while the code reads **`ENCRYPTION_KEY`** via `os.getenv` (`integrations/service.py:27`), which appears in neither `.env.example` nor compose. | cited | Forgeable tokens if the default ships; compose-based deployments cannot store credentials at all. | Fail fast on startup if secrets are unset/weak outside `development`. Unify on one validated setting. |
| **S-10** | **High [P1]** | **Refresh-token revocation bypass when Redis is down.** On any Redis exception `_validate_refresh_token_in_redis` returns `"FALLBACK"` and `refresh_access_token` accepts the token (revoked or not). | `auth/service.py:60-69,188-190` | Logout/rotation become meaningless during an outage (fail-open). | Fail closed (503) or persist refresh jti in Postgres. |
| **S-11** | **High [P1]** | **No RBAC / no tenant model.** `User` has only `plan`, no role; no org/workspace. Isolation is `user_id` equality in each handler (consistently applied in the routers I read). A new endpoint that forgets the filter is cross-user by default. | `models.py:108-155`; `engine/router.py:52-64` | Not enterprise-ready; no admin separation. | Introduce workspaces + roles + a central authorization layer (`WHERE workspace_id` via repository/RLS). |
| **S-12** | **High [P1]** | **Open signup, no email verification, no password reset, no lockout/MFA.** `is_verified` exists but is never enforced. Rate limit keys on `get_remote_address` (behind Render's proxy this is the proxy IP → throttling is global or ineffective); only auth routes are limited. | `auth/service.py:98-110`; `core/rate_limit.py:4`; `planner/router.py` (no limiter) | Fuels C-1/C-3 and LLM-cost abuse. | Verify email, trust-proxy-aware client IP, per-user limits on expensive endpoints. |
| **S-13** | **High [P1]** | **Workflow DSL accepted unvalidated via `POST/PATCH /workflows`**, plus `status` accepted as an arbitrary string (invalid values → DB error/500). | `crud/router.py:62-71,148,179-183` | Bypasses every validation and planner safety check. | Validate with `WorkflowDSL` + business validator at write time; enum for `status`. |
| **S-14** | **Medium [P1]** | **OAuth/API tokens are not refreshed durably.** Gmail refresh obtains a new access token but never persists it, and calls Google's `tokeninfo?access_token=…` on every execution (`gmail.py:100-130`). Because the app logs at `INFO` (`main.py:234-238`) and httpx logs request URLs at INFO, access tokens are likely logged (library behaviour, not run-verified). HubSpot (30-min access tokens), Salesforce, and Slack rotation have no refresh logic. | `executors/gmail.py:89-130` | Token leakage in logs; recurring auth failures. | Central `TokenManager` that refreshes and re-encrypts; never put tokens in URLs. |
| **S-15** | **Medium [P1]** | **CORS misconfiguration.** `allow_origin_regex` permits *any* `https://*.vercel.app` and any `localhost:port` with `allow_credentials=True` (`main.py:163-170`); `_add_cors_headers` **reflects any `Origin`** with credentials on error responses (`main.py:129-134`). | cited | Any Vercel-hosted attacker site can call the API from a victim's browser (bearer tokens limit exploitation but not enumeration). | Explicit origin list per environment only. |
| **S-16** | **Medium [P1]** | **Verbose error disclosure**: global handler returns `str(exc)` to clients (`main.py:151`); OAuth callback reflects up to 300 chars of provider error text into the redirect (`router.py:132-135`); `/health` reveals provider key presence. | cited | Information leak. | Generic errors + correlation IDs. |
| **S-17** | **Medium [P1]** | **Credentials persist after "disconnect"** (soft `is_active=False`; ciphertext retained). Stripe key can be saved but no executor exists. `integrations` unique key is `(user_id, service_name, display_name)` while upserts ignore `display_name`. | `integrations/service.py:300-327`; `models.py:464-466` | Data-retention/clean-up gaps. | Hard-delete ciphertext on disconnect; revisit uniqueness. |
| **S-18** | **Medium [P2]** | **Single static Fernet key, no key ID/rotation**; decrypt failure returns `None` and is surfaced as "not connected". | `integrations/service.py:26-42`; `credential_resolver.py:155-162` | No rotation path; misleading errors. | `MultiFernet` + key versioning (or KMS/Vault). |
| **S-19** | **Medium [P2]** | **Prompt injection** (see §6). | | | Structured outputs, allow-listed actions, approval for sensitive operations. |
| **S-20** | **Medium [P2]** | **Webhook triggers not implemented**, so no verification exists. `WebhookTriggerConfig.secret` is schema-only; `scheduler.webhook_listen` maps to `TriggerExecutor`. | `dsl/schema.py:163-167`; `registry.py:77`; grep of `/hooks` | If added carelessly this becomes an attack surface. | Build with HMAC + timestamp + replay protection from day one. |
| **S-21** | **Low [P2]** | `access` tokens non-revocable (15 min); refresh token stored in `localStorage` (XSS-stealable, `apiClient.js:10`); user enumeration via 409 on signup and via timing on login (no dummy hash when user missing, `auth/service.py:139-141`). | | | HttpOnly cookie for refresh, constant-time login path. |
| **S-22** | **Low [P2]** | Sentry `traces_sample_rate=1.0`/`profiles_sample_rate=1.0` (`main.py:37-42`) – cost and potential data capture; `load_dotenv` runs after `get_settings()` (`main.py:35,45`). | | | Config hygiene. |
| **S-23** | **Informational** | SQL injection: all queries I read use the ORM with bound parameters. The only f-string SQL is `ALTER TYPE … ADD VALUE '{new_val}'` over a constant tuple (`main.py:70-72`), not user-controlled. Password hashing uses bcrypt (`auth/utils.py:21-30`). JWT checks `type` claim and algorithm list (`auth/utils.py:74-79`). | | | Keep. |
| **S-24** | **Informational** | Not every file was read (see §18 coverage), so SQLi/authz absence is "not found in files read", not proven. | | | Complete in Stage 2 with SAST + review. |

**Can credentials leak into outputs, prompts, logs, DB, API responses?**
- *Workflow outputs/prompts:* **Yes** via `{{env.*}}` (C-3).
- *Logs:* **Likely** (tokens in URLs via httpx INFO logging; `[HTTP] METHOD url` log at `http.py:52`, which logs URLs that may embed secrets).
- *DB:* `WorkflowRunStepLog.input_json` stores resolved params including any secret (`runner.py:388`); `WorkflowRun.trigger_payload` is stored raw.
- *API responses:* run detail DTOs omit step I/O (good), but Execute-Step returns outputs (shallow scrub). `workers/router.py` would return `node_outputs` but is not mounted.
- Fernet-encrypted integration credentials never leave the server through `list_user_integrations` (verified: only id/service/display name).

---

## 8. Integration Audit

Everything here is by code reading; **no integration test exists and none was run.** "Tests" = tests that exercise that integration.

| Integration | Implemented | Authentication | Execution | Error handling | Tests | Status |
|---|---|---|---|---|---|---|
| **Gmail** (`get_emails`, `send_email`) | Yes (REST via httpx) | Google OAuth, offline access, shared "google" token stored under `gmail` row | Real API calls; scheduler path lacks `user_id` → fails | Auth/HTTP errors → `ExecutorResult.fail`; refresh **not persisted**; token in URL; no 429/backoff | None | **IMPLEMENTED BUT UNTESTED** (partially broken for scheduled runs). `create_draft` mapped to *send* → **BROKEN** semantics |
| **Google Sheets** | Yes (4 ops) | Same Google token | Real | Not fully reviewed; no refresh persistence | None | IMPLEMENTED BUT UNTESTED (file only partially read) |
| **Google Calendar** | Yes (2 ops) | Shares Gmail helpers | Real | Same limits | None | IMPLEMENTED BUT UNTESTED |
| **Google Drive** | Yes (3 ops + generic fallback executor) | Shares Gmail helpers | Real; `google_drive.*` unknown ops fall back to a generic executor (`registry.py:140-142`) | Same limits | None | PARTIALLY IMPLEMENTED |
| **Slack** | Yes (`post_message`) | OAuth bot token; channel ID context fetch | Real | No rate-limit (429) handling; `patch_slack_channel.py` suggests past data fixes | Validator tests for placeholder channels only (`test_sprint1.py:368-430`) | IMPLEMENTED BUT UNTESTED |
| **Notion** | `append_row` only | OAuth (Basic auth exchange) | Real | Minimal | None | PARTIALLY IMPLEMENTED |
| **HubSpot** | append/update/find | OAuth; **no refresh logic** (access tokens expire) | Real | Minimal | None | PARTIALLY IMPLEMENTED – will break after token expiry |
| **Salesforce** | OAuth connect only | OAuth | **No executor** | – | None | NOT IMPLEMENTED (execution) |
| **Stripe** | API-key storage only | Secret key encrypted | **No executor** | – | None | NOT IMPLEMENTED (execution) |
| **HTTP** | Yes | Caller supplies headers | Real; SSRF (S-6); retried 3× on any failure | Maps status/transport errors; follows no redirects (httpx default) | None | IMPLEMENTED BUT UNTESTED; **unsafe** |
| **Groq LLM nodes** | Yes (generate/classify/extract) | Server-wide key (not per-user); no per-user budget | Real; `classify` confidence is binary 1.0/0.0 (`ai_agent.py:128`); `extract` swallows JSON errors → `{}` | Exceptions propagate to runner retry | None | IMPLEMENTED BUT UNTESTED |
| **OpenAI nodes** | Alias of Groq | n/a | n/a | n/a | None | **MOCK / PLACEHOLDER** |
| **Twilio / WhatsApp / Airtable** | Enum values + DB enum patch only | none | none | – | None | NOT IMPLEMENTED |
| **LangGraph tools** (email/SMS/sheet) | Simulated success | – | `tools.py:36-114` | – | None | **MOCK / PLACEHOLDER** |
| **Resend test mail** | Yes | Server API key | Real, unauthenticated | try/except | None | IMPLEMENTED; **must be removed** (S-5) |

No integration has idempotency keys, bounded-retry classification by status code, or `Retry-After` support. **None may be classified production-ready.**

---

## 9. Database and Persistence Audit

| Area | Finding | Evidence | Risk / Action |
|---|---|---|---|
| Schema management | **No migrations.** Hand-written `schema.sql` (310 lines) + SQLAlchemy models + startup `ALTER TYPE … ADD VALUE` for `google_drive`, `airtable`, `twilio` (`main.py:66-77`). `Base.metadata.create_all` is not called anywhere (grep). `execution_events` exists only in `models.py:566-579`, not in `schema.sql`. `IntegrationService` enum in models lacks `airtable`/`twilio` that the DB patch adds. **Drift is certain.** | | P1: adopt Alembic; baseline from the live schema. |
| `celery_task_id` | Used by `tasks.py:95` and `workers/router.py:65,76,107` but **absent from the `WorkflowRun` model and `schema.sql`** → `AttributeError` if the workers router were mounted; silently a non-persisted attribute in the task. | `models.py:344-406` | Dead/broken code. |
| Foreign keys | Present with `ON DELETE CASCADE` for users→workflows/runs/integrations/api_keys; edges→nodes. `WorkflowRun.parent_run_id` FK without ondelete. `ExecutionEvent.run_id` has **no FK**. | `models.py` | P2. |
| Unique constraints | `users.email` unique; `edges_unique_connection`; `integrations_unique_per_user` is `(user_id, service_name, display_name)` (mismatch with upsert logic). `workflows` has no `(user_id, name)` constraint. **No unique key for run idempotency.** | `models.py:313,465` | P1: add `idempotency_key` unique per workflow. |
| Indexes | Single-column indexes on most FKs/status. No composite `(workflow_id, created_at)` for run history, none on `execution_events(run_id, id)` beyond single columns. | `models.py` | P2. |
| Transactions | Per-statement commits sprinkled across runner (`_update_run_status`, `_emit_event`, `_write_step_log`); errors swallowed with rollback. Planner save is one transaction (`planner/service.py:123-198`). CRUD `create/update` commits the workflow **then** `_sync_workflow_nodes` in a second transaction → partial state possible. | `runner.py:502-600`; `crud/router.py:151-155,185-189` | P1: unit-of-work with explicit boundaries. |
| Workflow versions | **None** (counter only). | `models.py:222-223` | P0 for target architecture: immutable `workflow_versions`, `runs.workflow_version_id`. |
| Workflow runs / execution state | Status columns + JSONB `context_snapshot`/`output_json` that `WorkflowRunner` never writes. No lease/heartbeat/worker-id. No `timed_out`/`waiting` states. | `models.py:344-406` | P0: stuck-run problem. |
| Tenant isolation | By `user_id` only; no row-level security; no workspace. | | P1. |
| Integration credentials | Fernet ciphertext in `integrations.credentials_encrypted`; no key id, no rotation; soft-delete retains ciphertext. | `integrations/service.py` | P1. |
| Audit logs | `AuditLog` model/table exists; grep of `backend/**/*.py` finds it only in `models.py` and a re-export in `database/__init__.py` – **never instantiated** anywhere. | `models.py:535-563` | NOT IMPLEMENTED (table only). |
| Soft delete | `deleted_at` on users/workflows; `delete_workflow` does not unschedule the APScheduler job (`crud/router.py:193-210`) → scheduled runs may keep firing for deleted workflows until `execute_scheduled_workflow` finds `deleted_at` (it does check). Lower risk. | | P2. |
| Node sync | `_sync_workflow_nodes` upserts but never deletes removed nodes; step-log lookup depends on `config_json["dsl_id"]`. Planner and CRUD write different `config_json` shapes. | `crud/router.py:15-56`; `planner/service.py:161-170` | P2: remove mirror tables or make them derived. |
| Session handling | `pool_size=10`, `max_overflow=20` per process; a new `SessionLocal` per background task; APScheduler's job store opens its own engine. | `database/session.py` | Connection pressure on Supabase pooler. |

---

## 10. Background Execution and Scheduler Audit

**Which mechanism runs what (verified):**

| Entry point | Mechanism | Runtime | Durable? | Credentials? |
|---|---|---|---|---|
| `POST /workflows/{id}/run` | FastAPI `BackgroundTasks` (`engine/router.py:185`) | `WorkflowRunner` (in-process) | **No** | Yes (`user_id` passed) |
| `POST /workflows/{id}/nodes/{nid}/execute` | Inline in the request | `WorkflowRunner.execute_single_node` | n/a | Yes |
| Cron/interval/date schedule | APScheduler `AsyncIOScheduler` inside each API process (`scheduler/service.py`) | `WorkflowRunner` (`jobs.py:89`) | Job definitions: yes (SQLAlchemyJobStore). Runs: no | **No** (`user_id` omitted) |
| Celery `run_workflow_task` | **No producer**; only `run_scheduled_workflow` (`tasks.py:183`) enqueues it, and nothing schedules `run_scheduled_workflow` (no `beat_schedule`, no RedBeat entry creation found in grep) | `LangGraphRuntime` | would be (`acks_late`) | **No** (`runtime.py:85-106`) |

Findings:
- **Celery is not responsible for any live execution path.** `README` and `docker-compose.yml` imply it is. Compose runs worker, beat and **Flower** (port 5555, no authentication configured) for nothing.
- **Duplicate scheduling risk (High):** every API replica starts its own APScheduler against the same `apscheduler_jobs` table (`main.py:80-91`). APScheduler does not support multiple schedulers on one job store; `max_instances=1` is per-process (`scheduler/service.py:89-93`). With `--reload`/multi-worker/replicas jobs can fire twice.
- **Worker-failure handling:** none for the live path. `max_attempts=3` in `workflow_runs` is a column, not enforced anywhere.
- `workers/router.py` (run status via Celery) is **not included in `main.py`** (grep) and would crash on `celery_task_id`.
- Scheduler lifecycle swallows start errors (`main.py:87-89`), so the app can run with a dead scheduler while `/health` says `status: ok`.
- `scheduler/jobs.py` ignores `workflow.status` (`draft`/`paused`) except via `pause_job`.

---

## 11. Testing Audit

Full details: [`TEST_BASELINE.md`](./TEST_BASELINE.md).

| Metric | Value |
|---|---|
| Test files | 5 (`conftest.py` + 4 test modules); `backend/tests/` only |
| Tests collected | **81** (`pytest --noconftest --co`) |
| Unit tests | Essentially all 81 (DTOs, registry metadata, validators, capability matching, event bus, regression guards) |
| API/integration tests | **1** (`test_health.py`, requires importing the full app) |
| End-to-end tests | **0** |
| Security tests | 3-4 narrow (`snapshot_excludes_secrets`, `_scrub_secrets`); **none** for SSTI/eval/SSRF/authz/OAuth |
| Workflow execution tests | A few `execute_single_node` tests with fakes (`test_sprint2.py:143-296`); **none** run a multi-node graph, retries, conditions, loops, or persistence |
| LLM/planner tests | **0** |
| Frontend tests | **0** (no runner in `package.json`) |
| CI | **None** (`.github/` absent) |

**Execution results (actually run, 2026-11-01, Python 3.14.7, no deps installed per Stage-1 rules):**
- `python -m pytest backend/tests -p no:cacheprovider -q` → **collection error** in `conftest.py` (`ModuleNotFoundError: sentry_sdk`). 0 tests run.
- `python -m pytest backend/tests --noconftest -p no:cacheprovider -q` → **77 failed, 2 passed, 1 skipped, 1 error** (all 77 failures `ModuleNotFoundError: No module named 'redis'` via `backend/auth/service.py:11`; the 1 error is the `client` fixture missing because conftest was bypassed; the 1 skip is a documented frontend-module skip).
- **Conclusion: the suite's real pass rate is unknown.** I did not claim any test passes. The environment lacks the project's dependencies (and Python 3.14 may be unsupported by several of them – unverified).

Missing critical scenarios: auth (refresh/rotation/Redis-down), tenant isolation, SSTI/eval/SSRF, runner retry/condition/loop/failure routing, scheduled run with credentials, restart/resume, idempotency, OAuth state, planner malformed-output retry, migrations, frontend flows.

---

## 12. Deployment and Operations Audit

Can a new developer clone and run it reliably from the docs? **No.**

| Item | Finding | Evidence |
|---|---|---|
| README | Describes `npm create vite … react-ts`, a `/workers` dir that doesn't exist, and `pip freeze` – no run/deploy instructions. | `README.md:5-45` |
| `.env.example` | Missing `JWT_SECRET_KEY`, `ENCRYPTION_KEY`/`FERNET_KEY`, `ALLOWED_ORIGINS`, `FRONTEND_URL`, `GOOGLE_*`/`SLACK_*`/`NOTION_*`/`HUBSPOT_*`/`SALESFORCE_*` client IDs/secrets and redirect URIs, `RESEND_API_KEY`, `EMAIL_FROM`, `BACKEND_URL`, `SENTRY_DSN`. Uses `VITE_API_BASE_URL` while code reads `VITE_API_URL`. Required `DATABASE_URL`/`REDIS_URL` have no defaults (`config.py:33-36`). | `.env.example`; `apiClient.js:14` |
| docker-compose | Titled "Production" but runs `uvicorn --reload` with source bind-mounts and Vite dev server. **No DB initialisation** (no `schema.sql` mount/Alembic) → first request fails on missing tables. `x-backend-env` omits `ENCRYPTION_KEY`, OAuth vars, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `RESEND_API_KEY`, `ALLOWED_ORIGINS`. Postgres `postgres/postgres` and unauthenticated Redis published on host ports; Flower exposed with no auth. `version: '3.8'` obsolete. | `docker-compose.yml:16-24,29-60,64-90,148-173` |
| Dockerfile.backend | Single-stage `python:3.11-slim`, runs as **root**, no `HEALTHCHECK`, `COPY . .` (includes `.git`, root scripts with secrets unless `.dockerignore` exists – none listed). Compose healthcheck uses `curl` (installed). | `Dockerfile.backend` |
| Dockerfile.frontend | Dev server only; no production build/nginx. Production uses Vercel (`vercel.json`). | `Dockerfile.frontend` |
| Entrypoints | `main.py:243` runs on port **3000** while compose/frontend default to **8000**; `uvicorn.run("main:app")` wouldn't resolve with the `backend.` package layout. | `main.py:241-243` |
| Health checks | `/health` always returns `status: ok` even if DB/Redis are down (the flags are separate fields); no readiness vs liveness. | `main.py:194-222` |
| Logging | `logging.basicConfig(INFO)` set at the *end* of `main.py` (L234) after loggers are used; unstructured text; no request/run correlation IDs. | `main.py:233-238` |
| Monitoring / error reporting | Sentry optional (100 % traces). No metrics, no OpenTelemetry. `observability.py` is local timers. | |
| Production config | `DEBUG` parser silently maps unknown strings to `False`; hard-coded fallbacks to `autoflow-ai-1.onrender.com` and `autoflow-ai-ebon.vercel.app` baked into source (`integrations/service.py:120-121`, `router.py:33`, `config.py:30`). | |
| Deployment docs | Design docs exist (`docs/*`, `Architecture.md`) but several describe features that are not implemented (event-sourced durable runtime, human approval, `SUSPENDED` state). | `Architecture.md:19-20,52-62,91` |

---

## 13. Technical Debt

1. Two parallel runtimes (`WorkflowRunner`, `LangGraphRuntime`) plus an unused Celery stack; documentation overstates the architecture.
2. Duplicate credential lookup logic: `CredentialResolver` *and* per-executor DB queries (`gmail.py:61-82`, `slack.py:52-76`, `hubspot.py:42-56`, `notion.py:44-58`).
3. Duplicate persistence models: DSL JSONB **and** node/edge tables, written in two inconsistent shapes.
4. Three overlapping validation layers (`dsl/validator.py`, `validator/`, `validation_pipeline.py`, `frontend/utils/validationPipeline.js`).
5. Swallow-everything error handling (`except Exception: pass/return None`) across runner, credential resolver, executors.
6. Dead/stale code: `workers/router.py`, `check_hash.py`, `extract_url.py`, `query_db.py`, `patch_slack_channel.py`, `frontend/src/mockData.js` (still imported by `MarketplacePage.jsx:18`), `FERNET_KEY` setting.
7. Comments that contradict the code ("sandboxed", "filtered"), which is how the C-1/C-3 issues survived review.
8. Sprint-numbered test files (`test_sprint1..3`) instead of domain-organised suites; no pytest config.
9. `DSL` fields that are accepted but not honoured (`error_policy`, `timeout_seconds`, `execute_once`, `always_output_data`, edge `condition`).
10. Hard-coded environment names/URLs in source.

---

## 14. Target Architecture Compatibility

| Target element | Present today? | Compatibility / gap |
|---|---|---|
| React + Vite + React Flow | **Yes** (React 19, Vite 8, `@xyflow/react` 12) | **Reuse.** Needs run-detail, approval, and version views; the canvas/inspector/registry context can be kept. Add tests. |
| FastAPI + PostgreSQL + SQLAlchemy | Yes | **Reuse with refactor** (Alembic, repositories, transactions, auth hardening). |
| Pydantic versioned DSL | Partial (`WorkflowDSL` with `compiler_version`, `migration_version`) | **Reuse + redesign:** make versions immutable, explicit edges (not both pointers *and* edges), typed condition/expression AST, no free-form `Dict[str, Any]` params for sensitive capabilities. |
| Graph validation | Partial (`validator/checks/graph.py`, routing consistency) | **Reuse**; add cycle/parallel-join/reachability semantics matched to the new executor. |
| Static capability registry | Partial (`capability_registry.py`, `node_registry.py`) | **Reuse** – natural seed for the capability registry with `sensitivity`, `idempotency`, `side_effect` metadata. |
| Deterministic policy engine | **Not present** | **Build.** (approvals, egress, rate/budget, sensitivity classes.) |
| LangGraph for planning/clarification/diagnosis | Present but only as an unreachable agent runtime with mocked tools | **Replace runtime usage;** reuse the idea. Planner can be re-expressed as a LangGraph plan → clarify → generate → validate graph. |
| Temporal Python SDK | **Absent** | **Build from scratch.** Wrap each executor as an Activity; deterministic `WorkflowRunner` replacement; signals/updates for approval; add Temporal to compose. |
| Failure classifier / AI recovery proposals / policy validation / reconciliation / approvals | **Absent** (`_classify_error` is substring matching, `engine/router.py:378-393`) | **Build from scratch**, seeded by that error taxonomy (credential/integration/compiler/validation/node). |
| Idempotency | **Absent** | **Build:** key per (run, node, attempt-independent), executor contracts. |
| PostgreSQL run projections / approvals / audit | Partial tables (`workflow_runs`, step logs, `audit_logs`, `execution_events`) | **Refactor:** runs become projections of Temporal history; add versions/approvals tables; actually write audit records. |
| Redis only transient | Used for refresh-token store and slowapi; Celery broker | **Refactor:** move refresh tokens to Postgres, drop Celery/Flower/RedBeat. |
| OpenTelemetry/structured logs/metrics | **Absent** | **Build.** |
| No arbitrary LLM-generated Python | Currently violated by `eval()` and Jinja | **Remove** (C-1/C-2). |
| "AI proposes; deterministic code disposes" | Partially honoured by planner validation; violated by CRUD bypass | **Enforce** at one write path. |
| Immutable workflow version per run | **Absent** | **Build.** |

**Reuse / Refactor / Replace / Build summary**
- **Keep/reuse:** frontend canvas + inspector + registry context; `dsl/schema.py` (as v1 seed); capability/node registries; validator check modules; planner prompt/retry structure; bcrypt/JWT helpers; Fernet wrapper (after key management fix); OAuth provider config table; executor HTTP logic (after hardening).
- **Refactor:** auth service, integrations/OAuth, CRUD router, scheduler (→ Temporal schedules), credential resolution (single path), models/migrations, executors (idempotency + error taxonomy).
- **Replace:** `context.py` template engine, `builtin.ConditionBranchExecutor`, `runner.py`, Celery/LangGraph runtime, `BackgroundTasks` execution, APScheduler-in-API, `docker-compose.yml`.
- **Build:** Temporal workflows/activities, versioning, policy engine, approval flow, idempotency store, failure classifier + recovery proposals, reconciliation, OpenTelemetry, CI, E2E tests, webhook ingestion, RBAC/workspaces.

---

## 15. Recommended Migration Strategy

*(Recommendation only — nothing is migrated in Stage 1.)*

**Phase 0 – Containment (days, before anything else).** Rotate leaked DB/user credentials and any env value reachable via C-3 (`JWT_SECRET_KEY`, `ENCRYPTION_KEY` → re-encrypt, API keys, OAuth client secrets). Purge git history. Disable `/nodes/{id}/execute`, `gmail/test-send`, and unauthenticated LLM endpoints (or gate them) until fixed.

**Phase 1 – Safe foundation.** Alembic baseline; settings validation (fail-fast); CI (lint, pytest with a pinned Python 3.11/3.12 image, Postgres service); remove `env` namespace, `eval`, switch to sandboxed/explicit expressions; write-path validation for DSL; email verification; fail-closed refresh; CORS fix.

**Phase 2 – Versioned model.** `workflow_versions` (immutable DSL JSON + hash), `workflow_runs.workflow_version_id`, run idempotency key, workspaces/roles, central authz layer, audit-log writes.

**Phase 3 – Durable execution.** Add Temporal (single namespace, one worker process). Implement a *deterministic* interpreter workflow over the immutable DSL; wrap executors as Activities with idempotency keys, timeout/retry policies by error class; run projection writer; remove Celery/Flower/BackgroundTasks/APScheduler (use Temporal Schedules); webhook ingestion with HMAC.

**Phase 4 – Intelligence and governance.** Capability registry with sensitivity; deterministic policy engine; approval via signals/updates; failure classifier + structured recovery proposals validated by policy; reconciliation activities; LangGraph for plan/clarify/diagnose; planner eval dataset and prompt versions.

**Phase 5 – Operations.** OpenTelemetry traces/metrics/structured logs, production compose/Helm-free deployment, backups, runbooks, load tests, frontend E2E (Playwright).

Strangler approach: keep the current API contract (`/workflows`, `/run`, run history) so the existing frontend keeps working while internals are swapped.

---

## 16. Prioritized Implementation Backlog

| # | Priority | Task | Rationale |
|---|---|---|---|
| 1 | **P0** | Rotate DB + user credentials leaked in `query_db.py`/`check_hash.py`; purge history; delete scripts | C-4 |
| 2 | **P0** | Remove `env` namespace; move to `SandboxedEnvironment`+`StrictUndefined` (or explicit reference resolver); raise on unresolved templates | C-1, C-3 |
| 3 | **P0** | Delete `eval()` in `ConditionBranchExecutor`; typed condition model | C-2 |
| 4 | **P0** | Gate/disable Execute-Step `params_override` and unauthenticated endpoints (`gmail/test-send`, `/transcribe`, `/ai/parse-intent`, `/followup/questions`); add email verification | S-5, S-12 |
| 5 | **P0** | HTTP executor SSRF/egress controls | S-6 |
| 6 | **P0** | Fix scheduled-run identity (`user_id`, `workflow_id`, status check) or retire APScheduler-in-API | scheduled runs can't use integrations |
| 7 | **P1** | Alembic baseline + CI + pinned Python/dep lockfile; make test suite runnable (`conftest` must not import the full app) | §11, §9 |
| 8 | **P1** | Immutable workflow versions; run → version FK; validate DSL on every write | durability, auditability |
| 9 | **P1** | OAuth hardening: signed single-use state + PKCE, no JWT in URL, durable token refresh, hard-delete on disconnect | S-7, S-8, S-14, S-17 |
| 10 | **P1** | Auth hardening: fail-closed refresh, secrets validation at startup, `ENCRYPTION_KEY`/`FERNET_KEY` unification, trust-proxy rate limits, CORS allow-list | S-9, S-10, S-12, S-15 |
| 11 | **P1** | Idempotency model for runs and per-node side effects; error-class-aware retries | duplicate side effects |
| 12 | **P1** | Introduce Temporal; port runner semantics; remove BackgroundTasks/Celery/LangGraph runtime | durability, restart safety |
| 13 | **P2** | Real tests: runner semantics, authz/tenant, SSTI/SSRF regression, executor contract tests with recorded HTTP, planner malformed-output tests, Playwright E2E | §11 |
| 14 | **P2** | Planner eval set + prompt versioning + redaction layer | §6 |
| 15 | **P2** | Honour or remove unused DSL fields; implement parallel/fan-out/join or remove from product claims | §5 |
| 16 | **P2** | Production compose/Dockerfile (non-root, healthchecks, migrations job, secrets), README/`.env.example` rewrite | §12 |
| 17 | **P3** | Observability stack (OTel, metrics), audit-log UI, workspaces/roles, approvals UX | target architecture |

---

## 17. Production Readiness Verdict

**Prototype.**

Evidence:
- **P0 security defects** that allow any registered user to escalate to code execution and secret disclosure (C-1, C-2, C-3), plus committed production credentials (C-4).
- **No durable execution**, no cancellation, no idempotency, no resume (§4 Q8-Q10).
- **Core capability gaps vs. product claims:** no parallel execution, no webhooks, integrations with no executor, scheduled runs unable to use credentials, "AI agent" tools simulated.
- **Zero demonstrated test coverage of the execution path**, and the suite could not run in a clean environment.
- **Not reproducible** from the repository docs.

It is a credible early prototype with a good domain model and UI, and the planner/validator chain is a genuine asset. The honest label for the current state is: *works in demos by the author's own deployment; unproven and unsafe for multi-tenant public use.*

*What I did **not** observe:* I did not start the application, hit any endpoint, or run any exploit. I cannot state that the happy path (plan → run → Gmail send) works end-to-end today; the git history (recent commits fixing a `NameError` in the background task) suggests the author got it working on their deployment.

---

## 18. Inspection Coverage and Limitations

**Read in full or substantially:** `backend/main.py`, `core/config.py`, `core/rate_limit.py`, `auth/{service,utils,dependencies,router}.py`, `auth/schemas.py` (grep), `database/{models,session}.py`, `database/schema.sql` (statement grep), `workflow/engine/{context,runner,router,credential_resolver,registry}.py`, executors `{http,builtin,ai_agent}.py`, `gmail.py` L60-258, `workflow/dsl/schema.py`, `workflow/planner/service.py`, `workflow/crud/router.py`, `workflow/langgraph_engine/{runtime,graph_builder (L1-120),tools (L1-120)}.py`, `scheduler/{service,jobs}.py`, `workers/{tasks,router,celery_app}.py`, `integrations/{service,router}.py`, `gmail/{router,service}.py`, `intent_parser/{router,service}.py`, `followup_engine/router.py`, tests (enumerated, partially read), `docker-compose.yml`, `Dockerfile.*`, `.env.example`, `README.md`, `requirements.txt`, root scripts.

**Grep/enumerate only (not read line-by-line):** executors `slack, notion, hubspot, google_sheets, google_calendar, google_drive`; `workflow/planner/{prompt,editor_engine,editor_service,router,schemas}.py`; `workflow/validator/**` and `validation_pipeline.py`; `workflow/node_registry.py`, `capability_registry.py`; `langgraph_engine/nodes.py,state.py`; `scheduler/router.py`; `routes/transcribe.py` (first 50 lines); `services/whisper_service.py`; `intent_parser/gemini_followup.py`; `docs/**`; all of `frontend/src/**` except `apiClient.js` and `package.json`/`vercel.json` greps; git history beyond the last 5 commits.

**Not performed:** dynamic testing, dependency vulnerability scan (`pip-audit`/`npm audit`), secret scan of full git history (only the two root files were examined), load testing, review of live deployments (Render/Vercel/Supabase).
