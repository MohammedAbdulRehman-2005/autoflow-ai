# Test Baseline — AutoFlow AI X (Stage 1)

Recorded 2026-11-01. Nothing in the repository was modified. No dependency was installed (Stage-1 rule), `PYTHONDONTWRITEBYTECODE=1` and `-p no:cacheprovider` were used so no files were written into the repo.

## Environment

| Item | Value |
|---|---|
| OS / shell | Windows, PowerShell 7 |
| Python | 3.14.7 (system interpreter, no virtualenv) |
| Working dir | `d:\autoflow-ai` |
| Relevant packages **present** | fastapi 0.141.1, httpx 0.28.1, Jinja2 3.1.6, pydantic 2.13.5, pydantic-settings 2.15.0, SQLAlchemy 2.0.54, psycopg2-binary 2.9.13, pytest 9.1.1, pytest-asyncio 1.4.0, pytest-cov 7.1.0 |
| Packages **absent** (observed via import errors or `pip list`) | `sentry_sdk`, `redis`, and (not in `pip list` output) celery, langgraph, groq, apscheduler, slowapi, bcrypt, python-jose |
| Postgres / Redis | Not available / not started |
| Pinned vs. declared | `backend/requirements.txt` mixes unpinned (`>=`) and a few pinned (`httpx==0.27.2`, `openai==1.41.0`, `python-dotenv==1.01`). **There is no lockfile.** The system has `httpx 0.28.1`, i.e. differs from the pin. |
| Project Python target | `Dockerfile.backend` uses `python:3.11-slim`. Whether all dependencies support 3.14 is **unverified**. |

## Test inventory

| File | Tests (collected) | Nature |
|---|---|---|
| `backend/tests/test_health.py` | 1 | App-level (`TestClient(app)` — imports the whole app) |
| `backend/tests/test_sprint1.py` | 32 | DSL fields, `ExecutionContext`, `CredentialResolver` (mock DB), `NodeRegistry`, condition-key/Slack-placeholder/routing validators, `EventBus` |
| `backend/tests/test_sprint2.py` | 23 (1 skip) | `ErrorPolicy`/DSL back-compat, `execute_single_node` with fakes, `_scrub_secrets`, `_classify_error`, registry/DTO shape |
| `backend/tests/test_sprint3.py` | 25 | Capability registry, editor-service helpers, schemas, `apply_patch` signature regressions |
| `backend/tests/conftest.py` | – | `client` fixture that does `from backend.main import app` (imports **every** router, Sentry, Redis, Celery-free but APScheduler etc.) |
| **Total collected** | **81** (`pytest --noconftest --co`) | |

Per-file counts come from counting `def test_` entries in the file listing (1+32+23+25 = 81, matching pytest's collected total).

## Runs

### Run A — default configuration

```
Command : python -m pytest backend/tests -p no:cacheprovider -q --no-header
Result  : COLLECTION ERROR — 0 tests executed
Error   : backend\tests\conftest.py:3  from backend.main import app
          backend\main.py:11           import sentry_sdk
          ModuleNotFoundError: No module named 'sentry_sdk'
```

### Run B — bypassing conftest (diagnostic only)

```
Command : python -m pytest backend/tests --noconftest -p no:cacheprovider -q --no-header
Result  : 77 failed, 2 passed, 1 skipped, 1 error  (81 collected)
```

| Outcome | Count | Cause |
|---|---|---|
| passed | 2 | Not identified individually; I make no claim about which tests these were. |
| failed | 77 | All: `ModuleNotFoundError: No module named 'redis'` raised from `backend/auth/service.py:11` (imported transitively by test modules). |
| error | 1 | `test_health.py::test_health_check` — `fixture 'client' not found` (an artefact of `--noconftest`). |
| skipped | 1 | `test_sprint2.py:533` — "mutationService.js is a frontend module — skipped in Python tests." (explicit skip in code) |

Why the failures are classified as environmental: the single dominant error is a missing third-party import. It is **not** evidence about the code under test. Likewise the 2 passes are **not** evidence of a healthy suite.

## What this baseline does and does not tell us

- **Cannot claim any test passes.** The true pass/fail state with correct dependencies is **UNKNOWN**.
- **Frontend:** no test runner is configured (`frontend/package.json` has only `dev`, `build`, `lint`, `preview`); `npm` was not run.
- **Coverage:** not measured.
- **Integration/E2E:** none exist; no test touches Postgres, Redis, a real HTTP provider or the LLM.

## Environmental blockers to a clean baseline (for Stage 2 planning)

1. Dependencies not installed (rule: no installs in Stage 1). A fresh venv from `backend/requirements.txt` + `requirements-dev.txt` on **Python 3.11** (the Dockerfile's version) is required.
2. `conftest.py` imports the full application, so *every* test requires Sentry, Redis client, slowapi, APScheduler, etc. and (at `TestClient(app)` startup) tries to start the scheduler and connect to Postgres/Redis.
3. Tests set `SECRET_KEY` (`test_sprint1.py:22`) while the settings class reads `JWT_SECRET_KEY`; `DATABASE_URL`/`REDIS_URL` are required settings with no defaults (`core/config.py:33-36`).
4. No `pytest.ini`/`pyproject.toml`: no `asyncio_mode`, no markers, no `pythonpath` — tests rely on running from repo root.
5. No CI to establish a reference result.

## Recommended Stage-2 baseline procedure (not executed)

```
python3.11 -m venv .venv && .venv/Scripts/activate
pip install -r backend/requirements.txt -r backend/requirements-dev.txt
set DATABASE_URL=postgresql://…   (disposable Postgres)  REDIS_URL=redis://…  JWT_SECRET_KEY=test…  ENCRYPTION_KEY=<fernet>
python -m pytest backend/tests -q --cov=backend --cov-report=term-missing
```
Record pass/fail/skip, then add coverage for the gaps listed in `PRODUCTION_READINESS_AUDIT.md` §11.
