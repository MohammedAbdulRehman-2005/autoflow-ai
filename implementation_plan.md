# Deploy AutoFlow AI X to Railway.app

This document outlines the strategy for deploying the AutoFlow AI X monorepo to production using Railway.app. Railway makes it incredibly easy to deploy monorepos with multiple services (Backend, Frontend, Celery Worker, PostgreSQL, Redis) from a single GitHub repository.

## User Review Required

> [!WARNING]
> Please review this plan carefully. Once approved, I will implement all necessary configuration files, Dockerfiles, and code changes to make the repository "Railway-ready". You will then be able to deploy it with just a few clicks in the Railway dashboard.

## Proposed Changes

### 1. Railway Configurations & Dockerfiles
We will configure Railway to build and run our services directly from the monorepo root.

#### [NEW] [railway.toml](file:///d:/autoflow ai/railway.toml)
We will add a root `railway.toml` config, or separate `railway.toml` files inside `backend/` and `frontend/` to declare the build and start commands for Railway's Nixpacks builder.
- **Backend**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Worker**: `celery -A workers.celery_app worker --loglevel=info`
- **Beat**: `celery -A workers.celery_app beat --loglevel=info`

*Alternatively, we will adapt our existing Dockerfiles to serve as the build targets for Railway.*

#### [MODIFY] [backend/main.py](file:///d:/autoflow ai/backend/main.py)
- **CORS Setup**: Update the `CORSMiddleware` configuration to allow requests from the Railway frontend URL (`https://autoflow-*.up.railway.app`) instead of just `localhost`.
- **Health Check**: Ensure a `GET /health` endpoint is configured and returns a 200 OK status.
- **Sentry Setup**: Integrate `sentry-sdk` for error monitoring.
- **Rate Limiting**: Integrate `slowapi` for basic endpoint rate limiting.

### 2. Frontend Configuration

#### [MODIFY] [frontend/vite.config.ts](file:///d:/autoflow ai/frontend/vite.config.ts) (if present)
- Adjust the API base URL resolution to point to the Railway backend domain instead of localhost when building for production.

### 3. Production Environment Checklist

Once the code is pushed, you will need to set these variables in the Railway dashboard for the backend service:
- `DATABASE_URL` (Provided automatically by Railway Postgres plugin)
- `REDIS_URL` (Provided automatically by Railway Redis plugin)
- `GROQ_API_KEY` or `OPENAI_API_KEY`
- `GOOGLE_CLIENT_ID` & `GOOGLE_CLIENT_SECRET`
- `JWT_SECRET_KEY` (Generate a new secure, random string)
- `FERNET_KEY` (For encrypting integration credentials in DB)
- `SENTRY_DSN` (From Sentry.io)
- `DEBUG=false`

## Step-by-Step Railway Deployment Guide

Once the code changes are pushed:
1. Go to **Railway.app** > **New Project** > **Deploy from GitHub repo**.
2. Select the AutoFlow AI X repo.
3. Railway will try to auto-detect the service. We will create **4 separate services** from the same repo:
   - **Frontend**: Set Root Directory to `/frontend`, build with Node/Vite.
   - **Backend**: Set Root Directory to `/`, specify `backend/Dockerfile` as the Dockerfile path.
   - **Celery Worker**: Set Root Directory to `/`, specify `backend/Dockerfile`, override start command to `celery -A backend.workers.celery_app worker...`.
   - **Celery Beat**: Same as Worker, override start command to run Celery beat.
4. Add the **PostgreSQL** and **Redis** plugins to your Railway project.
5. Link the DB variables (`DATABASE_URL`, `REDIS_URL`) to your Python services.
6. Generate a custom domain for your frontend (e.g., `app.autoflow.ai`) and backend (e.g., `api.autoflow.ai`) in Railway's network settings.
7. Update the backend CORS to allow `https://app.autoflow.ai`.

## Open Questions

> [!IMPORTANT]
> 1. Do you already have a Sentry account set up, or should I just add the code and leave the `SENTRY_DSN` blank for you to fill later?
> 2. Railway charges per minute for running services. Are you comfortable running a dedicated Celery Beat scheduler continuously, or would you prefer a cheaper alternative like using an external cron service to trigger an API endpoint?
> 3. Should I go ahead and implement these changes directly into the codebase right now?
