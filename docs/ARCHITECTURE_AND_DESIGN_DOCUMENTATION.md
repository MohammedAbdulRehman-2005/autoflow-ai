# AutoFlow AI X — Software Architecture & Design Documentation (SDD / SAD)

**Document Version:** 1.0.0  
**Status:** Canonical Software Design Document (SDD) & Systems Architecture Document (SAD)  
**Single Source of Truth Reference:** `MASTER_TECHNICAL_DOCUMENTATION_v2.md`  
**Target Audience:** Principal Systems Architects, UML Specialists, Software Engineers, Academic Evaluators  

---

## Table of Contents
1. [High-Level System Architecture](#1-high-level-system-architecture)
2. [Component Architecture](#2-component-architecture)
3. [Module Architecture](#3-module-architecture)
4. [Layered Architecture](#4-layered-architecture)
5. [Workflow Lifecycle](#5-workflow-lifecycle)
6. [Data Flow Diagrams (Level 0, 1, 2)](#6-data-flow-diagrams-level-0-1-2)
7. [Use Case Diagram & System Interactions](#7-use-case-diagram--system-interactions)
8. [Sequence Diagrams](#8-sequence-diagrams)
9. [Activity Diagrams](#9-activity-diagrams)
10. [State Machine Diagrams](#10-state-machine-diagrams)
11. [Deployment Architecture](#11-deployment-architecture)
12. [Database Architecture & Data Modeling](#12-database-architecture--data-modeling)
13. [Class Diagrams & Object Structural Relationships](#13-class-diagrams--object-structural-relationships)
14. [Runtime Architecture](#14-runtime-architecture)
15. [Security Architecture](#15-security-architecture)
16. [Integration Architecture](#16-integration-architecture)
17. [AI Architecture & Synthesis Loop](#17-ai-architecture--synthesis-loop)
18. [Design Principles](#18-design-principles)
19. [Design Patterns Implemented](#19-design-patterns-implemented)
20. [Engineering Decisions & Trade-off Matrix](#20-engineering-decisions--trade-off-matrix)

---

## 1. High-Level System Architecture

AutoFlow AI X operates as a distributed, AI-native automation platform designed to compile unstructured natural language business intent into deterministic, formally validated directed acyclic graphs (DAGs) executed across scalable runtime engines.

### 1.1 High-Level Architecture Diagram

```mermaid
graph TD
    subgraph ClientLayer [Client & Interactive Canvas Plane]
        FE[React 19 / Vite Single Page Application]
        Canvas[React Flow Workspace & Studio]
        Chat[AI Prompt Assistant Panel]
    end

    subgraph GatewayLayer [API & Gateway Plane]
        FastAPI[FastAPI Asynchronous Gateway /api/v1/*]
        AuthEngine[JWT Authentication Dependency]
        RateLimiter[SlowAPI Rate Limiter]
    end

    subgraph DomainLayer [Core Synthesis & Validation Plane]
        Planner[AI Workflow Planner Service]
        Validator[WorkflowValidator DAG Verification Engine]
        Registry[NodeRegistry Canonical Definition Store]
    end

    subgraph ExecutionLayer [Distributed Runtime & Task Plane]
        CeleryWorker[Celery Asynchronous Task Worker]
        DFSRunner[WorkflowRunner Iterative DFS Engine]
        LangGraph[LangGraph StateGraph Runtime Engine]
        Scheduler[APScheduler AsyncIOScheduler Service]
    end

    subgraph PersistenceLayer [Persistence & Infrastructure Plane]
        Postgres[(PostgreSQL 16 - Relational & JSONB Store)]
        Redis[(Redis - Broker / Cache / Revocation List)]
    end

    subgraph ExternalLayer [External SaaS & AI Plane]
        Groq[Groq API - Llama 3.3 70B / Whisper v3]
        SaaS[OAuth SaaS Providers: Gmail, Slack, Sheets, HubSpot, Notion]
    end

    FE --> FastAPI
    Canvas --> FastAPI
    Chat --> FastAPI
    FastAPI --> AuthEngine
    FastAPI --> RateLimiter
    FastAPI --> Planner
    FastAPI --> Validator
    FastAPI --> Registry
    Planner <--> Groq
    FastAPI --> CeleryWorker
    FastAPI --> Scheduler
    CeleryWorker --> DFSRunner
    CeleryWorker --> LangGraph
    DFSRunner --> Postgres
    LangGraph --> Postgres
    DFSRunner --> SaaS
    LangGraph --> SaaS
    Planner --> Postgres
    CeleryWorker <--> Redis
```

### 1.2 Subsystem Responsibilities, Inputs, Outputs, and Communication
| Subsystem | Responsibilities | Inputs | Outputs | Communication Mechanism |
| :--- | :--- | :--- | :--- | :--- |
| **Frontend UI** | Renders React Flow canvas, provides interactive node inspection, captures natural language prompts, and derives visual coordinates via Dagre. | User interactions, API JSON responses. | REST HTTP requests, canvas updates. | HTTPS/REST over browser `fetch` (`apiClient.js`). |
| **FastAPI Gateway** | Validates JWT bearer tokens, enforces IP/user rate limits (`SlowAPI`), routes endpoints, and manages application lifecycle. | HTTP requests (`POST`, `GET`, `PATCH`, `DELETE`). | Formatted JSON Pydantic responses (`200`, `201`, `202`, `400`, `401`, `422`). | WSGI/ASGI Uvicorn server protocol. |
| **AI Planner** | Compiles prompts into `WorkflowDSL`, injects few-shot schema specs, calls Groq LLM, and executes autonomous reflection/retry loops. | User prompt string, target industry, integration context. | Validated canonical `WorkflowDSL` Pydantic model. | REST over HTTPS to Groq (`llama-3.3-70b-versatile`). |
| **Validator** | Performs static DAG analysis: BFS reachability, Kahn's cycle detection, Jinja2 template reference validation, and credential checks. | `WorkflowDSL` JSON object. | `ValidationResult` (errors, warnings, `is_valid` flag). | In-memory synchronous Pydantic object evaluation. |
| **Database Layer** | Stores user identities, API keys, raw DSL JSON (`ai_context_json`), run execution telemetry, and encrypted OAuth tokens. | SQLAlchemy ORM models, SQL queries. | Transactional database rows, JSONB records. | TCP/IP connection pool (`psycopg2-binary`). |
| **Execution Engine** | Traverses graph either procedurally (`WorkflowRunner`) or statefully (`LangGraphRuntime`), resolving dynamic variables and executing plugins. | Celery task payload (`run_id`, `workflow_id`). | Execution step logs (`workflow_run_step_logs`), final run status. | Async Python execution inside Celery workers. |
| **External Services** | Third-party APIs providing email, messaging, CRM, spreadsheet operations, and LLM reasoning. | REST JSON payloads, OAuth 2.0 Bearer tokens. | External SaaS action confirmations, API payloads. | HTTPS REST requests via `http_client` / SDKs. |

---

## 2. Component Architecture

### 2.1 Complete Component Diagram

```mermaid
graph TD
    subgraph FrontendSPA [Frontend Component Plane]
        AuthComp[Authentication Component]
        BuilderComp[Workflow Builder Component]
        InspectorComp[Node Inspector Drawer]
    end

    subgraph BackendAPI [FastAPI Gateway Plane]
        AuthRouter[Auth Router]
        PlannerRouter[Planner Router]
        ValidatorRouter[Validator Router]
        EngineRouter[Engine Router]
        SchedulerRouter[Scheduler Router]
        IntegrationRouter[Integration Router]
    end

    subgraph CoreServices [Business Service Plane]
        AuthService[Auth Service & JWT Engine]
        PlannerService[AI Planner Service]
        ValidatorEngine[WorkflowValidator Engine]
        SchedulerService[APScheduler Singleton Service]
        OAuthService[OAuth Token & Credential Service]
    end

    subgraph WorkerRuntime [Distributed Runtime Plane]
        CeleryApp[Celery Distributed App]
        RunnerEngine[WorkflowRunner Engine]
        LangGraphEngine[LangGraphRuntime Engine]
        NodeRegistryComp[NodeRegistry & EXECUTOR_REGISTRY]
    end

    subgraph DataStorage [Storage & Telemetry Plane]
        DB[(PostgreSQL 16 Database)]
        CacheStore[(Redis Broker & Denylist)]
        AuditLogStore[Audit & Step Telemetry Logger]
    end

    AuthComp --> AuthRouter
    BuilderComp --> PlannerRouter
    BuilderComp --> ValidatorRouter
    BuilderComp --> EngineRouter
    InspectorComp --> EngineRouter
    AuthRouter --> AuthService
    PlannerRouter --> PlannerService
    ValidatorRouter --> ValidatorEngine
    EngineRouter --> CeleryApp
    SchedulerRouter --> SchedulerService
    IntegrationRouter --> OAuthService
    CeleryApp --> RunnerEngine
    CeleryApp --> LangGraphEngine
    RunnerEngine --> NodeRegistryComp
    LangGraphEngine --> NodeRegistryComp
    AuthService --> DB
    AuthService --> CacheStore
    PlannerService --> DB
    RunnerEngine --> DB
    RunnerEngine --> AuditLogStore
    LangGraphEngine --> DB
```

### 2.2 Component Specification Catalog
1. **Authentication Component:** Handles user registration (`/api/v1/auth/signup`), login (`/api/v1/auth/login`), JWT access/refresh token rotation, and immediate refresh token revocation via Redis denylisting.
2. **Workflow Builder Component:** Dual-mode React Flow canvas running `dslToFlow()` to derive nodes/edges from `WorkflowDSL` and Dagre `flowLayout.js` for left-to-right positional ranking.
3. **AI Planner Component (`WorkflowPlannerService`):** Orchestrates intent detection, Groq prompt compilation, structural JSON extraction (`_extract_json`), Pydantic validation, and static DAG checking.
4. **Validator Component (`WorkflowValidator`):** Evaluates `WorkflowDSL` schemas before persistence or execution, detecting circular dependencies, unreachable nodes, missing variables, or missing integration credentials.
5. **Runtime Component (`WorkflowRunner` / `LangGraphRuntime`):** Dual-mode runtime dispatching either iterative DFS graph traversal (`WorkflowRunner`) or LangGraph state machine execution (`LangGraphRuntime`).
6. **Scheduler Component (`SchedulerService`):** Singleton wrapping `AsyncIOScheduler` with `SQLAlchemyJobStore`, reconciling database schedule state at startup (`lifespan`).
7. **OAuth & Integration Component:** Manages OAuth 2.0 authorization code exchanges, encrypting access tokens via symmetric application encryption (`AES-256-GCM`).
8. **Node Registry Component (`NodeRegistry` & `EXECUTOR_REGISTRY`):** Canonical registry mapping declarative service/operation tuples (`NodeDefinition`) to executable concrete classes (`BaseExecutor`).

---

## 3. Module Architecture

### 3.1 Module Directory Catalog & Main Files
```
autoflow-ai/
├── backend/
│   ├── auth/              # JWT, bcrypt hashing, schemas, dependencies.py, router.py, service.py
│   ├── core/              # config.py (Pydantic Settings), redis.py, rate_limit.py (SlowAPI)
│   ├── database/          # models.py (10 SQLAlchemy models), session.py (SessionLocal)
│   ├── followup_engine/   # Interactive follow-up question generator for ambiguous prompts
│   ├── integrations/      # OAuth 2.0 flow handlers, token encryption, router.py, service.py
│   ├── intent_parser/     # Keyword intent detection and Gemini follow-up question generation
│   ├── routes/            # Standalone API endpoints (transcribe.py Whisper v3 handler)
│   ├── scheduler/         # AsyncIOScheduler wrapper, jobs.py, router.py, service.py
│   ├── services/          # whisper_service.py (Groq Whisper Large v3 speech-to-text)
│   ├── workers/           # celery_app.py (Celery config), tasks.py (async run_workflow_task)
│   ├── workflow/
│   │   ├── crud/          # CRUD router.py for Workflows and WorkflowNode DB synchronization
│   │   ├── dsl/           # schema.py (WorkflowDSL Pydantic models), validator.py
│   │   ├── engine/        # runner.py (WorkflowRunner), context.py, registry.py, executors/
│   │   ├── langgraph_engine/ # runtime.py (LangGraphRuntime), graph_builder.py, state.py
│   │   ├── planner/       # prompt.py, service.py (Groq LLM planning & reflection), router.py
│   │   └── validator/     # validator.py, checks/ (graph.py, schema.py, condition_keys.py)
│   └── main.py            # FastAPI lifespan, CORS, RateLimiter, Sentry middleware assembly
└── frontend/
    └── src/
        ├── components/    # Navbar.jsx, Sidebar.jsx, WorkflowNode.jsx, NodeInspector.jsx
        ├── context/       # AuthContext.jsx (<AuthProvider>)
        ├── pages/         # DashboardPage.jsx, WorkflowBuilderPage.jsx, LoginPage.jsx, LogsPage.jsx
        ├── services/      # apiClient.js, authApi.js, workflowApi.js, mutationService.js
        └── utils/         # flowLayout.js (Dagre LR auto-layout derivation)
```

### 3.2 Module Dependency Diagram

```mermaid
graph TD
    SubMain[backend/main.py] --> SubAuth[backend/auth]
    SubMain --> SubCore[backend/core]
    SubMain --> SubWorkflow[backend/workflow]
    SubMain --> SubScheduler[backend/scheduler]
    SubMain --> SubIntegrations[backend/integrations]
    SubMain --> SubWorkers[backend/workers]

    SubWorkflow --> SubDSL[workflow/dsl]
    SubWorkflow --> SubValidator[workflow/validator]
    SubWorkflow --> SubPlanner[workflow/planner]
    SubWorkflow --> SubEngine[workflow/engine]
    SubWorkflow --> SubLangGraph[workflow/langgraph_engine]

    SubPlanner --> SubDSL
    SubPlanner --> SubValidator
    SubEngine --> SubDSL
    SubLangGraph --> SubDSL
    SubLangGraph --> SubEngine

    SubWorkers --> SubEngine
    SubWorkers --> SubLangGraph
    SubScheduler --> SubWorkers
```

---

## 4. Layered Architecture

```mermaid
graph TB
    subgraph L1 [1. Presentation & Interaction Layer]
        P1[React 19 SPA / Vite 6]
        P2[React Flow Visual Studio]
        P3[Tailwind CSS / Framer Motion]
    end

    subgraph L2 [2. HTTP Gateway & Security Layer]
        S1[FastAPI API Router]
        S2[JWT Bearer Dependency]
        S3[SlowAPI Rate Limiter / CORS]
    end

    subgraph L3 [3. Business Domain & Synthesis Layer]
        B1[AI Workflow Planner Service]
        B2[WorkflowValidator Engine]
        B3[NodeRegistry Schema Store]
    end

    subgraph L4 [4. Execution & Distributed Task Layer]
        E1[Celery Task Workers]
        E2[WorkflowRunner Iterative DFS Engine]
        E3[LangGraphRuntime State Engine]
    end

    subgraph L5 [5. Infrastructure & Persistence Layer]
        I1[PostgreSQL 16 - Relational & JSONB]
        I2[Redis - Message Queue & Revocation Denylist]
        I3[APScheduler SQLAlchemyJobStore]
    end

    subgraph L6 [6. External Integration & AI Layer]
        X1[Groq API - Llama 3.3 70B]
        X2[External OAuth SaaS Providers]
    end

    L1 --> L2
    L2 --> L3
    L3 --> L4
    L4 --> L5
    L3 --> L6
    L4 --> L6
```

---

## 5. Workflow Lifecycle

```mermaid
graph TD
    S1[User Input Prompt] --> S2[Intent Detection & Entity Extraction]
    S2 --> S3{Ambiguity Detected?}
    S3 -- Yes --> S3A[Generate Follow-up Questions & Return to Studio]
    S3 -- No --> S4[Assemble Prompt + System Spec + Few-Shot Examples]
    S4 --> S5[Groq LLM Generation - Llama 3.3 70B]
    S5 --> S6[Extract JSON _extract_json]
    S6 --> S7[Pydantic Structural Validation WorkflowDSL.model_validate]
    S7 -- Schema Error --> S10[Reflection & Self-Correction Retry Loop]
    S7 -- Valid Schema --> S8[Static Semantic DAG Validation validate_workflow_graph]
    S8 -- Graph Error --> S10
    S10 --> S10A{Attempt <= MAX_RETRIES?}
    S10A -- Yes --> S5
    S10A -- No --> S10B[Raise HTTP 422 Error]
    S8 -- Valid Graph --> S9[Persist Workflow & WorkflowNode DB Records]
    S9 --> S11[Derive React Flow Visual Studio Graph dslToFlow]
    S11 --> S12[Manual Trigger or Scheduled Dispatch]
    S12 --> S13[Dispatch Celery run_workflow_task]
    S13 --> S14{Contains ai_agent Node?}
    S14 -- No --> S15A[Execute via WorkflowRunner Iterative DFS]
    S14 -- Yes --> S15B[Execute via LangGraphRuntime State Machine]
    S15A --> S16[Write Telemetry to workflow_run_step_logs]
    S15B --> S16
    S16 --> S17[Finalize WorkflowRun Status: completed / failed]
```

---

## 6. Data Flow Diagrams (Level 0, 1, 2)

### 6.1 Level 0 Context Diagram

```mermaid
graph LR
    User[User / Automation Engineer] -- "Natural Language Prompts / Studio Interactions" --> System((AutoFlow AI X Platform))
    System -- "Workflow Studio Graph / Telemetry Logs" --> User
    System -- "Prompt Completion Request" --> Groq[Groq LLM Service]
    Groq -- "Generated DSL JSON" --> System
    System -- "API Action Execution" --> ExternalSaaS[External SaaS Providers: Gmail, Slack, Sheets]
    ExternalSaaS -- "Action Response / Status" --> System
```

### 6.2 Level 1 Data Flow Diagram

```mermaid
graph TD
    User[User] -->|1. POST Prompt| P1(AI Planning Process)
    P1 <-->|LLM Queries| Groq[Groq API]
    P1 -->|2. Validated DSL| DB[(PostgreSQL Store)]
    User -->|3. GET Workflow| P2(Studio Derivation Process)
    DB -->|4. DSL JSON| P2
    P2 -->|5. React Flow Graph| User
    User -->|6. POST Run| P3(Task Dispatch Process)
    P3 -->|7. Enqueue Task| RedisStore[(Redis Queue)]
    RedisStore -->|8. Dequeue Task| P4(Runtime Execution Engine)
    P4 <-->|9. Read Credentials / Write Logs| DB
    P4 -->|10. Execute Node Plugins| ExternalSaaS[SaaS Providers]
```

### 6.3 Level 2 Data Flow Diagram (Runtime Execution Engine Detailed)

```mermaid
graph TD
    TaskIn[Celery Worker Dequeue] --> ReadDSL[Read WorkflowDSL from DB]
    ReadDSL --> CheckAgent{Has ai_agent nodes?}
    CheckAgent -- No --> InitDFS[Initialize WorkflowRunner Engine]
    CheckAgent -- Yes --> InitGraph[Initialize LangGraphRuntime Engine]
    
    subgraph ExecutionSubprocess [Step Execution Subprocess]
        InitDFS --> NextNode[Pop Next Node from DFS Stack]
        NextNode --> ResolveTempl[Resolve Template Variables Context]
        ResolveTempl --> LookupCred[Decrypt OAuth Token via CredentialResolver]
        LookupCred --> ExecPlugin[Invoke BaseExecutor.execute]
        ExecPlugin --> WriteStep[INSERT INTO workflow_run_step_logs]
        WriteStep --> RouteBranch{Success or Failure?}
        RouteBranch -- Success --> PushNext[Push on_success Target to Stack]
        RouteBranch -- Failure --> EvalPolicy{ErrorPolicy?}
        EvalPolicy -- stop --> HaltRun[UPDATE workflow_runs status='failed']
        EvalPolicy -- continue --> PushFail[Push on_failure Target to Stack]
        EvalPolicy -- retry --> ApplyBackoff[Apply Exponential Backoff Retry]
    end
```

---

## 7. Use Case Diagram & System Interactions

```mermaid
graph LR
    actor User as Authenticated User
    actor Admin as Administrator
    actor SchedulerActor as APScheduler / Cron Trigger
    actor ExternalSaaS as External SaaS Service

    subgraph System [AutoFlow AI X Platform]
        UC1[Register & Authenticate Account]
        UC2[Plan Workflow from Natural Language]
        UC3[Edit & Configure Graph in Visual Studio]
        UC4[Connect OAuth Integration Provider]
        UC5[Manually Trigger Workflow Run]
        UC6[Schedule Recurring Workflow Execution]
        UC7[Inspect Execution Logs & Audit Trail]
        UC8[Execute Single Step in Isolation]
    end

    User --> UC1
    User --> UC2
    User --> UC3
    User --> UC4
    User --> UC5
    User --> UC6
    User --> UC7
    User --> UC8
    Admin --> UC7
    SchedulerActor --> UC6
    UC5 --> ExternalSaaS
    UC6 --> ExternalSaaS
    UC8 --> ExternalSaaS
```

---

## 8. Sequence Diagrams

### 8.1 User Authentication & Token Rotation Sequence

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Studio as Frontend Studio
    participant AuthRoute as FastAPI /auth Router
    participant AuthSvc as AuthService
    participant DB as PostgreSQL (users)
    participant Redis as Redis Denylist

    User->>Studio: Enter email & password
    Studio->>AuthRoute: POST /api/v1/auth/login
    AuthRoute->>AuthSvc: login_user(payload)
    AuthSvc->>DB: Query User & Verify bcrypt hash
    DB-->>AuthSvc: Valid User Model
    AuthSvc->>AuthSvc: Generate JWT access (15m) & refresh (7d)
    AuthSvc-->>AuthRoute: AuthResponse
    AuthRoute-->>Studio: Return Tokens
    Note over Studio: Token Rotation Flow
    Studio->>AuthRoute: POST /api/v1/auth/refresh (old refresh token)
    AuthRoute->>AuthSvc: refresh_access_token(token)
    AuthSvc->>Redis: Check denylist & store old refresh token
    AuthSvc->>AuthSvc: Issue new access & new refresh token
    AuthSvc-->>Studio: Return Rotated Tokens
```

### 8.2 Prompt Planning & Reflection Loop Sequence

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Studio as Frontend Studio
    participant PlanRoute as /ai/plan-workflow
    participant PlanSvc as WorkflowPlannerService
    participant Groq as Groq API (Llama 3.3 70B)
    participant Validator as WorkflowValidator
    participant DB as PostgreSQL (workflows)

    User->>Studio: Submit prompt string
    Studio->>PlanRoute: POST /api/v1/ai/plan-workflow
    PlanRoute->>PlanSvc: plan_workflow(prompt)
    PlanSvc->>Groq: Generate DSL (Prompt + Schema Spec)
    Groq-->>PlanSvc: Raw JSON text response
    PlanSvc->>PlanSvc: WorkflowDSL.model_validate(json)
    PlanSvc->>Validator: validate_workflow_graph(dsl)
    alt Validation Fails (Attempt <= MAX_RETRIES)
        PlanSvc->>Groq: Re-query with validation error trace
        Groq-->>PlanSvc: Corrected DSL JSON
    end
    PlanSvc->>DB: Save Workflow & WorkflowNode records
    DB-->>PlanSvc: Workflow UUID
    PlanSvc-->>Studio: PlanWorkflowResponse (id, dsl, stats)
```

### 8.3 Workflow Execution Sequence

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Studio as Frontend Studio
    participant Route as /workflows/{id}/run
    participant DB as PostgreSQL
    participant Celery as Celery Worker
    participant Runner as WorkflowRunner
    participant SaaS as External Integration API

    User->>Studio: Click "Run Workflow"
    Studio->>Route: POST /api/v1/workflows/{id}/run
    Route->>DB: Create WorkflowRun (status='pending')
    Route->>Celery: Dispatch run_workflow_task.delay(run_id)
    Route-->>Studio: HTTP 202 Accepted (run_id)
    Celery->>Runner: Initialize WorkflowRunner(dsl, run_id)
    loop For Each Node in DFS Traversal
        Runner->>Runner: Evaluate template references
        Runner->>SaaS: Execute API request via BaseExecutor
        SaaS-->>Runner: Return API result dictionary
        Runner->>DB: INSERT INTO workflow_run_step_logs
    end
    Runner->>DB: UPDATE workflow_runs status='completed'
```

### 8.4 OAuth Connection Flow Sequence

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Studio as Frontend Studio
    participant Route as /integrations/{provider}/connect
    participant OAuthSvc as IntegrationsService
    participant Provider as External OAuth Provider (e.g. Slack)
    participant DB as PostgreSQL (integrations)

    User->>Studio: Click "Connect Slack"
    Studio->>Route: GET /api/v1/integrations/slack/connect
    Route->>OAuthSvc: build_oauth_url(slack, user_id)
    OAuthSvc-->>Studio: Redirect URL with state token
    Studio->>Provider: Redirect to consent screen
    User->>Provider: Grant authorization
    Provider->>Route: GET /api/v1/integrations/callback/slack?code=...
    Route->>OAuthSvc: exchange_code_for_tokens(code)
    OAuthSvc->>Provider: Exchange authorization code for token payload
    Provider-->>OAuthSvc: Access token & refresh token
    OAuthSvc->>OAuthSvc: AES-256-GCM Encrypt tokens
    OAuthSvc->>DB: Save Integration record
    Route-->>Studio: Redirect to /settings?connected=slack
```

### 8.5 Scheduled Workflow Execution Sequence

```mermaid
sequenceDiagram
    autonumber
    participant Sched as APScheduler Service
    participant DB as PostgreSQL (apscheduler_jobs / workflows)
    participant Celery as Celery Task Worker
    participant Runtime as WorkflowRunner

    Note over Sched: Scheduled Cron Trigger Fires (e.g. 09:00 UTC)
    Sched->>DB: Load Workflow DSL & verify status == 'active'
    Sched->>DB: Create WorkflowRun record (status='pending')
    Sched->>Celery: Enqueue run_workflow_task.delay(run_id)
    Celery->>Runtime: Initialize runtime and execute graph
    Runtime->>DB: Write step logs & update run completion
```

---

## 9. Activity Diagrams

### 9.1 Prompt Planning & Reflection Activity Diagram

```mermaid
stateDiagram-v2
    [*] --> ReceivePrompt: User submits prompt
    ReceivePrompt --> ParseIntent: Extract SaaS tokens
    ParseIntent --> BuildPrompt: Assemble System Spec & Few-Shot Examples
    BuildPrompt --> CallLLM: Groq API Inference
    CallLLM --> ExtractJSON: Extract JSON substring
    ExtractJSON --> ValidateSchema: Pydantic WorkflowDSL.model_validate
    
    state ValidateSchema {
        [*] --> CheckPydantic
        CheckPydantic --> CheckReachability: BFS Reachability
        CheckReachability --> CheckCycles: Kahn's Cycle Sort
    }
    
    ValidateSchema --> IsValid: Check validation result
    IsValid --> SaveDB: Valid
    IsValid --> CheckRetries: Invalid
    CheckRetries --> CallLLM: Retries < MAX_RETRIES (Inject feedback)
    CheckRetries --> Error422: Retries Exhausted
    SaveDB --> [*]: Return Validated DSL
    Error422 --> [*]: Return Validation Errors
```

### 9.2 Node Step Execution Activity Diagram

```mermaid
stateDiagram-v2
    [*] --> LoadNode: Pop Node from DFS Traversal
    LoadNode --> ResolveTemplates: Interpolate {{node.output.field}}
    ResolveTemplates --> CheckCreds: Requires Integration Credential?
    CheckCreds --> DecryptToken: Yes (AES-256 Decrypt via CredentialResolver)
    CheckCreds --> LookupExecutor: No
    DecryptToken --> LookupExecutor: Attach Bearer Token
    LookupExecutor --> ExecutePlugin: Invoke BaseExecutor.execute
    ExecutePlugin --> CheckOutcome: Evaluate Execution Result
    CheckOutcome --> LogSuccess: Success
    CheckOutcome --> EvalErrorPolicy: Failure
    LogSuccess --> PushSuccessTarget: Route to on_success
    EvalErrorPolicy --> HaltRun: ErrorPolicy == stop
    EvalErrorPolicy --> PushFailureTarget: ErrorPolicy == continue
    EvalErrorPolicy --> ApplyBackoffRetry: ErrorPolicy == retry
    PushSuccessTarget --> [*]
    PushFailureTarget --> [*]
    HaltRun --> [*]
```

---

## 10. State Machine Diagrams

```mermaid
stateDiagram-v2
    [*] --> Draft: Created via Studio or AI Planner
    Draft --> Validated: Passes WorkflowValidator static checks
    Validated --> Active: Enabled by User
    Active --> Scheduled: APScheduler Cron Registered
    Active --> Running: Manual Trigger / Celery Task Picked Up
    Scheduled --> Running: Cron Trigger Fired
    Running --> Completed: All Nodes Executed Successfully
    Running --> Failed: Node Failed & ErrorPolicy == stop
    Failed --> Retry: RetryPolicy Triggered
    Retry --> Running: Re-execute Step
    Running --> Cancelled: Task Terminated by User
    Completed --> Active: Ready for next run
    Failed --> Active: Ready for next run
```

### 10.1 State Transition Definitions
- **Draft:** Newly created workflow or currently being edited; unverified against schema invariants.
- **Validated:** Graph reachability, cycle freedom, and template keys have passed static checks.
- **Active:** Workflow enabled and ready for manual or programmatic dispatch.
- **Scheduled:** Registered inside PostgreSQL `apscheduler_jobs` table.
- **Running:** Execution record created in `workflow_runs`; Celery task actively processing nodes.
- **Completed:** Terminal success state; all steps logged with `status = 'completed'`.
- **Failed:** Terminal failure state; an unrecoverable node error halted graph traversal.

---

## 11. Deployment Architecture

```mermaid
graph TD
    subgraph ClientDevice [User Client Device]
        Browser[Web Browser - SPA SPA Runtime]
    end

    subgraph HostingInfrastructure [Production Container Orchestration - Railway / Docker]
        subgraph StaticCDN [Frontend Container]
            ViteContainer[Nginx / Vite Static Hosting Container]
        end

        subgraph CoreAPI [Backend FastAPI Container]
            UvicornServer[FastAPI Application Server Port 8000]
            SchedulerInst[APScheduler Singleton Service]
        end

        subgraph WorkerPool [Distributed Celery Worker Container]
            CeleryService[Celery Worker - queues: default, high_priority, scheduled]
            BeatService[Celery RedBeat Scheduler Service]
        end

        subgraph DataTier [Persistent Managed Data Containers]
            PGContainer[(PostgreSQL 16 Instance)]
            RedisContainer[(Redis 7 Cache & Broker Instance)]
        end
    end

    subgraph ExternalCloud [External SaaS & AI API Cloud]
        GroqCloud[Groq Cloud API - Llama 3.3 70B]
        GoogleCloud[Google API Cloud - Gmail & Sheets]
        SlackCloud[Slack Cloud API]
        HubSpotCloud[HubSpot CRM Cloud API]
    end

    Browser -- HTTPS --> ViteContainer
    Browser -- HTTPS REST / Bearer JWT --> UvicornServer
    UvicornServer -- TCP Connection --> PGContainer
    UvicornServer -- Async Queue Push --> RedisContainer
    CeleryService -- Async Queue Pop --> RedisContainer
    CeleryService -- Read/Write Runs & Step Logs --> PGContainer
    SchedulerInst -- Read/Write Jobs --> PGContainer
    UvicornServer -- HTTPS REST --> GroqCloud
    CeleryService -- HTTPS REST --> GoogleCloud
    CeleryService -- HTTPS REST --> SlackCloud
    CeleryService -- HTTPS REST --> HubSpotCloud
```

---

## 12. Database Architecture & Data Modeling

### 12.1 Verified ER Diagram & Entity Structure

```mermaid
erDiagram
    users ||--o{ workflows : "owns"
    users ||--o{ api_keys : "issues"
    users ||--o{ integrations : "connects"
    users ||--o{ workflow_runs : "triggers"
    users ||--o{ audit_logs : "records"

    workflows ||--o{ workflow_nodes : "contains"
    workflows ||--o{ workflow_edges : "connects"
    workflows ||--o{ workflow_runs : "executes"

    workflow_nodes ||--o{ workflow_run_step_logs : "logs step"
    workflow_runs ||--o{ workflow_run_step_logs : "aggregates steps"
    workflow_runs ||--o{ workflow_runs : "parent retry"

    users {
        uuid id PK
        string email UK
        string password_hash
        user_plan plan
        int monthly_run_count
    }

    workflows {
        uuid id PK
        uuid user_id FK
        string name
        workflow_status status
        jsonb ai_context_json
        int version
    }

    workflow_nodes {
        uuid id PK
        uuid workflow_id FK
        node_type node_type
        jsonb config_json
        float position_x
        float position_y
    }

    workflow_edges {
        uuid id PK
        uuid workflow_id FK
        string source_node_id
        string target_node_id
        string condition_expr
    }

    workflow_runs {
        uuid id PK
        uuid workflow_id FK
        uuid user_id FK
        uuid parent_run_id FK
        run_status status
        jsonb output_json
        int attempt_number
    }

    workflow_run_step_logs {
        uuid id PK
        uuid run_id FK
        uuid node_id FK
        run_status status
        jsonb input_json
        jsonb output_json
        int duration_ms
    }

    integrations {
        uuid id PK
        uuid user_id FK
        string service_name
        string credentials_encrypted
    }
```

### 12.2 Key Indexing & Constraints
- **Primary Keys:** Every domain model uses UUIDv4 primary keys (`id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)`) except `audit_logs`, which uses a high-throughput integer sequence (`BIGSERIAL`).
- **Foreign Key Cascades:** `ON DELETE CASCADE` is applied from `Workflow` to `WorkflowNode`, `WorkflowEdge`, and `WorkflowRun`.
- **GIN JSONB Indexing:** Generalized Inverted Indexes (GIN) are enforced on `workflows.ai_context_json` and `workflow_run_step_logs.output_json` for high-performance JSON key queries.

---

## 13. Class Diagrams & Object Structural Relationships

```mermaid
classDiagram
    class WorkflowDSL {
        +UUID id
        +str name
        +int version
        +TriggerConfig trigger
        +List[WorkflowNodeDSL] nodes
        +List[WorkflowEdgeDSL] edges
        +model_validate(obj) WorkflowDSL
    }

    class WorkflowNodeDSL {
        +str id
        +NodeType type
        +ServiceType service
        +OperationType operation
        +str label
        +Dict params
        +str on_success
        +str on_failure
    }

    class WorkflowEdgeDSL {
        +str source_id
        +str target_id
        +str condition
    }

    class BaseExecutor {
        <<abstract>>
        +execute(params: Dict, context: ExecutionContext) Dict*
    }

    class GmailGetEmailsExecutor {
        +execute(params: Dict, context: ExecutionContext) Dict
    }

    class SlackPostMessageExecutor {
        +execute(params: Dict, context: ExecutionContext) Dict
    }

    class WorkflowRunner {
        -WorkflowDSL dsl
        -UUID run_id
        -Session db
        -ExecutionContext context
        +run() void
        -execute_node(node: WorkflowNodeDSL) Dict
    }

    class LangGraphRuntime {
        -WorkflowDSL dsl
        -UUID run_id
        -Session db
        +compile_dsl_to_graph() StateGraph
        +run() void
    }

    class ExecutionContext {
        +Dict node_outputs
        +Dict variables
        +resolve_template(expr: str) Any
    }

    class WorkflowValidator {
        +validate(dsl: WorkflowDSL) ValidationResult
    }

    WorkflowDSL "1" *-- "0..*" WorkflowNodeDSL : composition
    WorkflowDSL "1" *-- "0..*" WorkflowEdgeDSL : composition
    WorkflowRunner --> WorkflowDSL : executes
    WorkflowRunner --> ExecutionContext : maintains
    WorkflowRunner ..> BaseExecutor : instantiates
    LangGraphRuntime --> WorkflowDSL : compiles
    BaseExecutor <|-- GmailGetEmailsExecutor : inheritance
    BaseExecutor <|-- SlackPostMessageExecutor : inheritance
    WorkflowValidator --> WorkflowDSL : validates
```

---

## 14. Runtime Architecture

```mermaid
graph TD
    TriggerEvent[Celery run_workflow_task.delay] --> DequeueWorker[Celery Task Worker]
    DequeueWorker --> CheckAI{Contains ai_agent?}
    CheckAI -- No --> Runner[WorkflowRunner Iterative DFS Engine]
    CheckAI -- Yes --> LangGraph[LangGraphRuntime State Engine]

    subgraph DFSExecutionLoop [Iterative DFS Traversal Loop]
        Runner --> PopNode[Pop Next Node from Stack]
        PopNode --> Interp[Resolve Context & Templates]
        Interp --> Cred[CredentialResolver Decrypt Token]
        Cred --> RegistryLookup[Lookup Executor in EXECUTOR_REGISTRY]
        RegistryLookup --> Invoke[Executor.execute]
        Invoke --> WriteTelemetry[Write Step Log to DB]
        WriteTelemetry --> RouteBranch{Check Node Outcome}
        RouteBranch -- Success --> PushSuccess[Push on_success Node]
        RouteBranch -- Failure --> EvalPolicy[Evaluate ErrorPolicy]
    end
```

---

## 15. Security Architecture

```mermaid
graph TD
    subgraph ClientPlane [Client Plane]
        Browser[React Studio]
    end

    subgraph SecurityGateway [FastAPI Gateway Plane]
        BearerDep[get_current_user Bearer Auth]
        SlowAPI[SlowAPI Rate Limiter]
    end

    subgraph SecretsManagement [Credential Security Plane]
        CredResolver[CredentialResolver Singleton]
        AESCipher[AES-256-GCM / Fernet Cryptographic Engine]
        DBStore[(PostgreSQL integrations table)]
    end

    Browser -- "1. Request + Authorization: Bearer <JWT>" --> SlowAPI
    SlowAPI --> BearerDep
    BearerDep -- "2. Validate Signature & Expiry" --> BearerDep
    BearerDep -- "3. Valid User" --> Router[Protected Endpoint]
    Router -- "4. Request Integration Execution" --> CredResolver
    CredResolver -- "5. Read credentials_encrypted" --> DBStore
    DBStore -- "6. Encrypted Ciphertext" --> CredResolver
    CredResolver -- "7. Decrypt Token in Memory" --> AESCipher
    AESCipher -- "8. Decrypted OAuth Access Token" --> CredResolver
```

---

## 16. Integration Architecture

```mermaid
graph LR
    subgraph CoreEngine [AutoFlow AI X Core]
        Planner[AI Workflow Planner]
        Registry[NodeRegistry & EXECUTOR_REGISTRY]
        Runner[Execution Engine]
    end

    subgraph IntegrationExecutors [Concrete Executor Plugins]
        Gmail[GmailExecutors]
        Slack[SlackExecutors]
        Sheets[SheetsExecutors]
        HubSpot[HubSpotExecutors]
        Notion[NotionExecutors]
        HTTP[HttpRequestExecutor]
    end

    subgraph CloudAPIs [Target External Cloud APIs]
        GoogleAPI[Google Workspace REST API]
        SlackAPI[Slack Web API v2]
        HubSpotAPI[HubSpot CRM API v3]
        NotionAPI[Notion Database API v1]
        WebhookAPI[Arbitrary External Webhook Targets]
    end

    Planner --> Registry
    Runner --> Registry
    Registry --> Gmail
    Registry --> Slack
    Registry --> Sheets
    Registry --> HubSpot
    Registry --> Notion
    Registry --> HTTP
    Gmail --> GoogleAPI
    Sheets --> GoogleAPI
    Slack --> SlackAPI
    HubSpot --> HubSpotAPI
    Notion --> NotionAPI
    HTTP --> WebhookAPI
```

---

## 17. AI Architecture & Synthesis Loop

```mermaid
graph TD
    PromptIn[1. User Natural Language Input] --> IntentDetect[2. Keyword & Intent Extraction]
    IntentDetect --> PromptBuild[3. PromptBuilder System Assembly]
    PromptBuild --> InjectSchema[4. Inject Canonical JSON Schema & Examples]
    InjectSchema --> GroqCall[5. Groq Llama 3.3 70B Generation]
    GroqCall --> JSONExtract[6. _extract_json Substring Extraction]
    JSONExtract --> PydanticVal[7. WorkflowDSL.model_validate]
    PydanticVal -- Schema Error --> RetryBuild[10. Assemble Error Trace Feedback Prompt]
    PydanticVal -- Valid --> GraphVal[8. validate_workflow_graph BFS/Kahn Check]
    GraphVal -- Graph Error --> RetryBuild
    RetryBuild --> RetryCheck{Attempt <= MAX_RETRIES?}
    RetryCheck -- Yes --> GroqCall
    RetryCheck -- No --> Abort422[Raise HTTP 422 Unprocessable Entity]
    GraphVal -- Valid Graph --> OutputDSL[9. Canonical Validated Workflow DSL]
```

---

## 18. Design Principles

1. **Separation of Concerns:** Strict decoupling between representation (`WorkflowDSL`), graph validation (`WorkflowValidator`), visual studio rendering (`React Flow`), and execution runtimes (`WorkflowRunner` / `LangGraphRuntime`).
2. **Modularity & Extensibility:** Adding a new integration requires zero modifications to the runner or planner; developers simply add an executor subclass and register it in `NodeRegistry` and `EXECUTOR_REGISTRY`.
3. **Loose Coupling:** The FastAPI HTTP web server is fully decoupled from graph execution via asynchronous Celery message queues over Redis.
4. **High Cohesion:** Every module encapsulates a distinct domain responsibility (e.g., `backend/auth/` handles all JWT rotation and user sessions).
5. **Fault Tolerance & Reliability:** Execution steps support per-node `RetryPolicy` backoffs and `ErrorPolicy` routing (`stop`, `continue`, `retry`), ensuring transient network glitches do not fail entire automation runs.

---

## 19. Design Patterns Implemented

| Design Pattern | Implementation Module | Code Verification & Architectural Role |
| :--- | :--- | :--- |
| **Registry Pattern** | `backend/workflow/node_registry.py`<br>`backend/workflow/engine/registry.py` | Maintains static dictionaries (`NodeRegistry.nodes`, `EXECUTOR_REGISTRY`) mapping declarative keys to metadata and executor classes. |
| **Factory Pattern** | `backend/workflow/engine/registry.py` | `get_executor_for_node(node)` acts as a factory instantiating the concrete `BaseExecutor` subclass matching the node's `service` and `operation`. |
| **Strategy Pattern** | `backend/workflow/engine/runner.py`<br>`backend/workflow/langgraph_engine/` | Selects runtime strategy (`WorkflowRunner` procedural DFS vs `LangGraphRuntime` agent state graph) dynamically based on node composition. |
| **Dependency Injection** | `backend/auth/dependencies.py`<br>`backend/database/session.py` | FastAPI `Depends(get_db)` and `Depends(get_current_user)` inject transactional database sessions and authenticated user profiles directly into route handlers. |
| **Template Method** | `backend/workflow/engine/executors/base.py` | Abstract `BaseExecutor` defines the uniform interface `execute(params, context)` implemented by all concrete SaaS plugins. |

---

## 20. Engineering Decisions & Trade-off Matrix

| Engineering Decision | Chosen Technology | Evaluated Alternative | Architectural Trade-off & Justification |
| :--- | :--- | :--- | :--- |
| **Backend Web Framework** | **FastAPI (Python 3.12)** | Django REST Framework | **Advantage:** Asynchronous `asyncio` loop performance and automatic Pydantic/OpenAPI validation.<br>**Trade-off:** Lacks built-in admin UI; requires custom SQLAlchemy session management. |
| **Persistence Database** | **PostgreSQL 16** | MongoDB / NoSQL | **Advantage:** Full ACID referential integrity across workflows/runs/logs with native `JSONB` indexing for dynamic DSL schemas.<br>**Trade-off:** Requires explicit schema migrations (`schema.sql`) for core tables. |
| **Distributed Queue** | **Celery + Redis Broker** | Python `asyncio` BackgroundTasks | **Advantage:** Persistent task execution across server restarts, multi-queue routing, and horizontal worker autoscaling.<br>**Trade-off:** Introduces Redis broker operational dependency. |
| **Visual Studio Engine** | **React Flow (`@xyflow/react`)** | Custom HTML5 Canvas / D3.js | **Advantage:** Production-grade viewport virtualization, minimaps, custom node components, and Dagre layout integration.<br>**Trade-off:** Adds `@xyflow/react` bundle dependency. |
| **Canonical Spec** | **Workflow DSL (JSON Pydantic)** | YAML / Custom Scripting | **Advantage:** JSON compiles cleanly across REST APIs, frontend canvas state, and LLM structured generation.<br>**Trade-off:** Verbose syntax compared to raw YAML syntax. |
| **Primary LLM Engine** | **Groq Llama 3.3 70B** | OpenAI GPT-4o sole reliance | **Advantage:** Sub-second inference latency critical for interactive UI planning loops with low deterministic temperature (`0.2`).<br>**Trade-off:** Requires fallback configuration for complex speech/audio tasks. |
