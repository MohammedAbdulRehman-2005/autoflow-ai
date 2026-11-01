# Staging & Production Strategy — AutoFlow AI X

**Date**: 2026-11-01  
**Author**: Senior Backend Security & Reliability Engineering Audit  
**Status**: APPROVED ARCHITECTURE DIRECTIVE  
**Scope**: Deployment safety, infrastructure isolation, preview environments, and rollback protocols  

---

## 1. Objective & Non-Negotiable Rules

The objective of this strategy is to safely deploy, verify, and operate **AutoFlow AI X** across existing infrastructure providers (**Vercel**, **Render**, and **Supabase**) without risking production disruption, data corruption, or secret exposure.

### Non-Negotiable Operational Rules:
1. **Never connect development or test environments to production Supabase.**
2. **Never deploy unverified branches directly to production Render or Vercel production domains.**
3. **Never run database migrations against production without a verified snapshot and proven rollback script.**
4. **Every environment (Local Docker, Staging/Preview, Production) must maintain isolated credentials.**
5. **Production environment variables must not be altered without explicit owner authorization.**

---

## 2. Environment Matrix & Infrastructure Isolation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            ISOLATION BOUNDARIES                             │
└─────────────────────────────────────────────────────────────────────────────┘

 [Local Development / Test]      [Staging / Preview]             [Production]
 ──────────────────────────      ───────────────────             ────────────
 • Local Mock / SQLite / Docker  • Vercel Preview Branch Deploy  • Vercel Production
 • Local Redis 127.0.0.1         • Render Staging Web Service    • Render Production
 • Isolated Mock Credentials     • Supabase Staging Project      • Supabase Production
 • Zero External Side Effects    • Independent Test API Keys     • Production API Keys
```

| Component | Local Dev / Unit Tests | Staging / Preview Environment | Production Environment |
|---|---|---|---|
| **Frontend** | Vite Dev Server (`localhost:5173`) | Vercel Git Branch Preview (`https://autoflow-ai-git-*.vercel.app`) | Vercel Production (`https://autoflow-ai-ebon.vercel.app`) |
| **Backend API** | FastAPI (`localhost:8000`) / Docker | Render Web Service: `autoflow-ai-staging` | Render Web Service: `autoflow-ai-production` |
| **Database** | Ephemeral SQLite / Disposable Docker Postgres | Supabase Project: `autoflow-ai-staging` | Supabase Project: `autoflow-ai-prod` |
| **Redis** | Local Redis Container (`redis://localhost:6379/0`) | Render Redis Instance (Staging) | Render Redis Instance (Production) |
| **Celery Worker** | Local inline / disposable worker | Render Background Worker (Staging) | Render Background Worker (Production) |
| **Encryption Keys** | Fixed mock test Fernet key | High-entropy Staging `FERNET_KEY` | Dedicated Production `FERNET_KEY` |
| **JWT Secret** | Fixed mock test secret | Independent Staging `JWT_SECRET_KEY` | High-entropy Production `JWT_SECRET_KEY` |

---

## 3. Provider Setup & Safe Staging Implementation

### 3.1 Vercel (Frontend Preview Deployment)
Vercel natively creates isolated Preview Deployments for every Git branch and pull request:
1. **Branch Preview Trigger**: Pushing the verified upgrade branch (`feature/stage2-security-containment`) triggers an automatic Preview Deployment.
2. **Environment Variable Scoping in Vercel Dashboard**:
   - Set `VITE_API_URL` for **Preview** environment to the Render staging URL (`https://autoflow-ai-staging.onrender.com`).
   - Keep `VITE_API_URL` for **Production** environment pointing to `https://autoflow-ai-1.onrender.com`.
3. **CORS Alignment**: The backend CORS regex in `backend/main.py`:
   ```python
   re.compile(r"^https://autoflow-ai(-[a-zA-Z0-9_-]+)?\.vercel\.app$|^http://localhost:\d+$")
   ```
   automatically permits Vercel preview branches while rejecting arbitrary third-party domains.

### 3.2 Render (Backend API & Worker Staging)
To avoid deploying unverified backend code to live users:
1. **Create Staging Web Service on Render**:
   - Name: `autoflow-ai-staging`
   - Branch: `feature/stage2-security-containment` (or designated staging branch)
   - Dockerfile path: `./Dockerfile.backend`
   - Plan: Free or Starter
2. **Environment Variables for Render Staging**:
   - `ENVIRONMENT`: `staging`
   - `DEBUG`: `false`
   - `DATABASE_URL`: Staging Supabase Postgres URI (pooled connection string, transaction pooler port 6543)
   - `REDIS_URL`: Staging Redis connection URI
   - `JWT_SECRET_KEY`: Dedicated staging key (at least 32 random characters)
   - `FERNET_KEY`: Dedicated staging Fernet key
   - `ALLOWED_ORIGINS`: `https://autoflow-ai-staging.vercel.app,http://localhost:5173`
   - `UNSAFE_EVAL_ENABLED`: `false`
   - `ALLOW_INSECURE_HTTP`: `false`
3. **Separate Staging Background Worker (if Celery enabled)**:
   - Command: `celery -A backend.celery_app worker -l info`
   - Configured with identical staging environment variables.

### 3.3 Supabase (Database Isolation)
1. **Create Staging Supabase Project**:
   - In Supabase dashboard: **New Project** -> `autoflow-ai-staging`.
   - Select the same cloud region as the production project to minimize latency.
2. **Schema Initialization**:
   - Run Alembic migrations against the staging database:
     ```bash
     DATABASE_URL="postgresql://postgres:[PASSWORD]@[STAGING_HOST]:5432/postgres" alembic upgrade head
     ```
   - Verify all tables, enum types (`integration_service`, `workflow_status`, `error_policy`), and indexes exist.
3. **Zero Production Data Cloning**:
   - Do not copy user passwords, tokens, or personal data to staging.
   - Use synthetic seed data for functional verification.

---

## 4. Local Docker Fallback (When Staging Services are Unavailable)

If cloud provider limits (e.g. Render free tier limits or Supabase project quotas) prevent provisioning live staging services immediately, use the local containerized stack:

```bash
# 1. Build and launch isolated local stack
docker compose up -d postgres redis

# 2. Apply migrations locally
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/autoflow_dev" alembic upgrade head

# 3. Start local API and frontend
docker compose up backend frontend
```

The local Docker compose environment is configured with complete network isolation and does not make external side effects.

---

## 5. Promotion Pipeline: Verification to Production

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  Local / CI     │ ───> │  Vercel Preview │ ───> │  Owner Sign-off │ ───> │   Production    │
│  pytest 100%    │      │  + Render Stage │      │  Manual Review  │      │   Zero-Downtime │
└─────────────────┘      └─────────────────┘      └─────────────────┘      └─────────────────┘
```

### Stage 2 Exit Criteria (Before Promotion)
- [x] All 20 security regression tests pass.
- [x] All 80 legacy unit/integration tests pass.
- [x] Frontend builds cleanly with zero syntax/type errors.
- [x] Hardcoded credentials purged from working tree.
- [x] All exposed endpoints secured.

### Pre-Deployment Checklist for Production
1. **Owner Approval**: Explicit written approval from the repository owner.
2. **Database Backup**: Trigger manual backup in Supabase Dashboard (**Database** -> **Backups** -> **Create Backup**).
3. **Environment Audit**: Verify all production environment variables conform to strict security rules:
   - `JWT_SECRET_KEY` is not default.
   - `FERNET_KEY` is set and valid.
   - `ENVIRONMENT=production`.

---

## 6. Concrete Rollback Protocols

### 6.1 Backend API Rollback (Render)
If an unexpected failure or latency spike occurs on Render after deployment:
1. Navigate to **Render Dashboard** -> **autoflow-ai-production** -> **Deploys**.
2. Locate the previous healthy deployment commit hash.
3. Click the options menu (`...`) and select **Rollback to this deploy**.
4. Render immediately switches traffic back to the prior container image within 60 seconds without rebuilding.

### 6.2 Frontend Rollback (Vercel)
If the frontend UI encounters client-side runtime errors:
1. Navigate to **Vercel Dashboard** -> **Project: autoflow-ai** -> **Deployments**.
2. Select the previous stable production deployment.
3. Click **Instant Rollback**.
4. Edge CDN routing immediately restores the prior static build in under 5 seconds.

### 6.3 Database Migration Rollback (Supabase / Alembic)
If a database migration fails or introduces lock contention:
1. Connect via migration runner using the direct connection string.
2. Execute migration downgrade:
   ```bash
   alembic downgrade -1
   ```
3. If data corruption occurred, restore from the pre-deployment Supabase snapshot created in Step 5.
