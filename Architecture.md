# AutoFlow AI X: Architecture Specification

## 1. Vision & Design Principles

AutoFlow AI X bridges the gap between human intent and machine execution. We are evolving from a static workflow builder into a dynamic, intent-driven Agent Operating System.

### Core Principles
*   **Determinism at the Edge:** AI (probabilistic) is used strictly for planning and routing. Execution paths (nodes) and state management must be 100% deterministic, observable, and replayable.
*   **Evolution over Revolution:** We expand the existing foundation via refactoring. We do not throw away the working FastApi/Celery/React stack; we enhance it with event sourcing and formal graph compilation.
*   **Zero-Trust Execution:** Every node execution and external API call must be isolated, strictly authorized via RBAC, and prevented from leaking secrets.

## 2. System Context & Request Lifecycle

AutoFlow acts as an orchestrator sitting between Users (or third-party triggers), AI Models (Gemini/Groq), and Integrations (SaaS APIs).

**Request Lifecycle:**
1.  **Intent Ingestion:** User inputs natural language or triggers an event.
2.  **Compilation Pipeline:** The Planner parses intent, retrieves context via Semantic Memory, and emits a DAG (Directed Acyclic Graph) of operations.
3.  **Scheduling:** The Execution Graph is submitted to the durable Runtime.
4.  **Execution & Event Sourcing:** The Runtime dispatches tasks to Node Plugins. Every state change (Started, Suspended, Completed, Failed) is appended to an immutable `execution_events` ledger.
5.  **Telemetry:** Metrics and logs are streamed for UI visualization (Execution Tracer).

## 3. The Compilation Pipeline (Planner Architecture)

The system is transitioning from directly generating JSON DSL via a single prompt to a formalized **Multi-Pass Compiler**.

### 3.1 Pipeline Stages
*   **Pass 1: Intent Parsing:** Extract goals and variables using a lightweight LLM.
*   **Pass 2: Context Retrieval:** Query the Vector DB to find similar historical execution patterns.
*   **Pass 3: Semantic IR Generation:** Generate an Intermediate Representation.
*   **Pass 4: Optimization (Static Analysis):** The graph is analyzed. Sequential nodes with no data dependencies are converted to parallel execution paths.
*   **Pass 5: Grounding:** Map generic IR actions to concrete Node Plugins in the Registry.

*Architectural Decision:* **Multi-Pass Compilation vs Single-Prompt JSON Generation**
*   **Why:** Single-prompt generation suffers from high hallucination rates on complex graphs.
*   **Tradeoffs:** Higher latency for workflow creation; increased LLM costs.
*   **Evolution:** Start by separating Intent Parsing from DSL Generation before introducing the full IR.

## 4. Runtime & Execution Engine (Data Plane)

The most critical evolution of AutoFlow AI X is moving from a monolithic synchronous runner to an **Event-Sourced Durable Execution Engine**.

### 4.1 Execution State Machine
A workflow run is modeled as a state machine where transitions are driven by an immutable event log rather than in-place database updates.

*   **State Machine Transitions:**
    *   `PENDING` -> `RUNNING`
    *   `RUNNING` -> `SUSPENDED` (e.g., waiting for human approval or an external webhook)
    *   `SUSPENDED` -> `RUNNING` (upon wakeup event)
    *   `RUNNING` -> `FAILED` -> `RETRYING` -> `RUNNING`

### 4.2 Durable Execution (Event Sourcing)
Instead of updating `workflow_runs.status`, the engine appends events to a ledger (e.g., `execution_events` table). When a node fails or the worker crashes, the scheduler re-reads the ledger, restores the exact state, and resumes.

*Architectural Decision:* **Postgres-backed Event Ledger vs Temporal**
*   **Why:** Introducing Temporal requires a massive infrastructure shift (Java/Go services, Cassandra). To adhere to "Evolution over Revolution", we implement an append-only event ledger in the existing PostgreSQL database.
*   **Tradeoffs:** Lower throughput than Temporal; requires custom polling/pub-sub logic.
*   **Implementation Priority:** Phase 1 (Immediate).

### 4.3 Node Lifecycle & Plugin SDK
Nodes (Executors) must be strictly stateless. The Runtime injects the `ExecutionContext` (inputs, secrets) into the node. The node returns an `ExecutorResult`.
*   **Idempotency:** Plugins must be designed to be idempotent whenever possible, as the durable runtime guarantees *at-least-once* execution.

## 5. Security & Multi-Tenant Architecture

*   **Execution Sandbox:** We will progressively sandbox node execution. Initially, this is handled by strict Python module boundaries. Future iterations will utilize isolated V8 isolates/WebAssembly for custom code execution.
*   **Credential Handling:** Secrets are stored encrypted. They are never serialized into the Workflow DSL or passed to the LLM. They are resolved by a Vault service *just-in-time* inside the Node Executor.

## 6. Implementation Roadmap

To avoid a risky "big bang" rewrite, the architecture will be implemented in incremental phases:

### Phase 1: Event-Sourced Foundation (Current Focus)
*   **Goal:** Replace in-place updates of `workflow_runs` with an append-only `execution_events` ledger.
*   **Steps:**
    1.  Create `execution_events` migration.
    2.  Update the Workflow Engine to emit `ExecutionEvent` records.
    3.  Create a basic state hydrator (read events to determine current state).
*   **Compatibility:** Old runs remain; new runs use the event log.

### Phase 2: Compiler & Planner Refactoring
*   **Goal:** Break the Planner into Intent Parsing and Graph Generation passes.
*   **Steps:** Isolate LLM calls; introduce basic graph optimization (parallelization).

### Phase 3: Semantic Memory & Self-Healing
*   **Goal:** Introduce Vector DB (Qdrant/pgvector) for storing past execution DAGs and context.
*   **Steps:** Log successful graphs; query them during the Planning phase. Introduce a "Patch Agent" to handle failed Node execution errors.

## 7. Extension Points & Future Enhancements

*   **Human Approval Flow:** Utilizing the `SUSPENDED` state to halt execution and send a Slack/Email link to an authorized user to resume the DAG.
*   **MCP (Model Context Protocol):** Refactoring the Node Registry to dynamically ingest MCP servers rather than hardcoding integrations.
