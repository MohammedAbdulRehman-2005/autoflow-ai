# AutoFlow AI X

**AutoFlow AI X** is an AI-native workflow operating system that converts business requirements written in natural language into fully executable, self-monitoring automation workflows.

## Project Structure

- `/frontend`: User interface containing the visual workflow builder, built with React, Tailwind CSS, and React Flow.
- `/backend`: Core API handling prompt processing, workflow logic generation, and database interactions using Python FastAPI.
- `/workers`: Background task runners for executing workflows, managing retries, and scheduled jobs using Celery.
- `/shared`: Common code, TypeScript types, OpenAPI schemas, and constants shared across the monorepo.

## Initialization Commands

### Frontend
```bash
# Initialize Vite React app
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npm install reactflow @xyflow/react
```

### Backend
```bash
# Initialize FastAPI backend
mkdir backend
cd backend
python -m venv venv
# On Windows: venv\Scripts\activate | On Mac/Linux: source venv/bin/activate
pip install fastapi uvicorn sqlalchemy psycopg2-binary redis
pip freeze > requirements.txt
```

### Workers
```bash
# Initialize Celery workers
mkdir workers
cd workers
python -m venv venv
# On Windows: venv\Scripts\activate | On Mac/Linux: source venv/bin/activate
pip install celery redis
pip freeze > requirements.txt
```

## GitHub Repository Structure & Branch Naming

We use a feature-branch workflow for this repository:

- `main`: Production-ready code. Commits here should only come from merges from `dev` or `hotfix` branches.
- `dev`: Active development branch. All feature branches are merged here first for testing and integration.
- `feature/<feature-name>`: Short-lived branches for new features or improvements (e.g., `feature/visual-builder`, `feature/gmail-integration`).
- `hotfix/<issue-name>`: Urgent fixes for production issues that branch directly off `main` (e.g., `hotfix/login-crash`).
- `bugfix/<issue-name>`: Non-urgent bug fixes that branch off `dev`.
