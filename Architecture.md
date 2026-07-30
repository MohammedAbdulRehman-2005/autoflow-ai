# AutoFlow AI X: Architecture Specification

## 1. Vision

AutoFlow AI X aims to bridge the gap between human intent and machine execution by providing a resilient, intent-driven automation platform. The vision is to evolve from a static, declarative workflow builder into a dynamic, AI-orchestrated execution kernel. By combining natural language understanding with deterministic runtime guarantees, the platform empowers users to rapidly define, optimize, and execute complex business processes.

## 2. Design Principles

*   **Determinism at the Edge:** While AI is inherently probabilistic and used for planning and routing, the resulting execution paths must be deterministic, observable, and replayable.
*   **Evolution over Revolution:** The architecture must iteratively expand upon the existing foundation. We prioritize refactoring, modularization, and extension over complete rewrites, ensuring backward compatibility with existing workflows and plugins.
*   **Observability First:** Every state transition, AI decision, and external integration call must be fully traceable. Debuggability is a first-class citizen.
*   **Security in Depth:** The system must enforce strict zero-trust boundaries, particularly around the execution of AI-generated actions, credential access, and data isolation.

## 3. Architecture Goals

*   **Scalability:** Support high-throughput execution of both long-running asynchronous workflows and low-latency synchronous queries.
*   **Reliability:** Ensure fault tolerance through durable execution state, enabling pause, resume, and retry mechanics without data loss.
*   **Extensibility:** Provide a robust, standardized plugin architecture that allows internal teams and external contributors to rapidly integrate new capabilities.
*   **Enterprise Readiness:** Enforce strict compliance, auditing, role-based access control (RBAC), and deployment flexibility (cloud vs. on-premises).

## 4. Core Concepts

*   **Intent:** The human-readable goal or directive (e.g., "Onboard a new employee to Slack and Google Workspace").
*   **Planner:** The AI subsystem responsible for translating Intent into an actionable structure.
*   **Execution Graph:** A Directed Acyclic Graph (DAG) representing the sequence of operations, generated from the Planner.
*   **Runtime Engine:** The system responsible for safely executing the Graph, managing state transitions, and handling I/O.
*   **Node/Plugin:** An isolated unit of work (e.g., "Send Slack Message") within the Execution Graph.

## 5. High-Level Architecture

The AutoFlow AI X architecture is divided into three primary planes:

1.  **Control Plane (The API & Planner):** Handles incoming user intent, orchestrates the translation of intent into an Execution Graph, and manages metadata (RBAC, workflow definitions).
2.  **Data/Execution Plane (The Runtime):** A distributed engine that interprets the Execution Graph, dispatches tasks to workers, manages durable state, and integrates with external services.
3.  **Storage Plane (Memory & State):** Manages relational metadata, high-speed semantic caches, and episodic memory for AI context.

## 6. Component Architecture

### 6.1 Planner Architecture

The Planner translates raw intent into an actionable execution graph.

*   **Intent Processing:** Natural language is parsed to identify goals, entities, and constraints.
    *   *Why it exists:* To decouple natural language understanding from execution logic.
    *   *Benefits:* Allows swapping or upgrading underlying LLMs without impacting the execution engine.
    *   *Tradeoffs:* Adds latency to the initial workflow generation phase.
*   **Compiler Pipeline & DSL Evolution:** We are evolving the legacy JSON DSL into a more robust Intermediate Representation (IR). The compiler performs a dependency analysis pass to optimize the graph (e.g., identifying parallelizable tasks).
    *   *Why it exists:* To ensure that AI-generated plans are structurally sound before execution.
    *   *Benefits:* Catches hallucinations and invalid configurations at compile time rather than runtime.
    *   *Future Extensibility:* Allows the introduction of formal Semantic IR and advanced optimization passes (like pruning redundant API calls).

### 6.2 Runtime Architecture

The Runtime Engine executes the compiled DAG.

*   **Workflow Engine:** Evolving towards a durable execution model. Instead of relying purely on synchronous database locks, state transitions are treated as events.
    *   *Why it exists:* To manage long-running processes, delays, and human-in-the-loop approvals.
    *   *Benefits:* Workflows can survive server restarts; granular retries become trivial.
    *   *Tradeoffs:* Increases complexity in state management compared to a simple CRUD approach.
*   **Execution Model:** Workers pull tasks from a message bus, execute the specific Node Plugin, and return the result to the engine.

### 6.3 Memory Architecture

*   **Knowledge Layer & Context Management:** The system maintains an "Episodic Memory" of past successful executions and organizational context.
    *   *Why it exists:* To provide the Planner with historical context, preventing the AI from repeating past mistakes and allowing it to learn organizational preferences.
    *   *Benefits:* Vastly improves the accuracy of the Intent-to-Graph translation.
    *   *Future Extensibility:* Transitioning from simple JSON blobs to a formalized Vector/Graph database architecture for semantic retrieval.

### 6.4 Security Architecture

*   **Authentication & Authorization:** Standardized OAuth2/OIDC for user access, coupled with strict Role-Based Access Control (RBAC) at the API gateway level.
*   **Policy Engine:** Every execution node is evaluated against a centralized policy engine before dispatch.
    *   *Why it exists:* To prevent an AI hallucination from executing a destructive action (e.g., deleting a database) that the user does not have permission to perform.
    *   *Benefits:* Enforces zero-trust execution.
*   **Credential Management:** Secrets are never exposed to the LLM or stored in plaintext. The Runtime Engine securely injects required credentials at the exact moment of API execution.

### 6.5 Observability

*   **Logging, Metrics, & Tracing:** The platform emits structured logs and distributed traces (e.g., OpenTelemetry) for every node execution.
    *   *Why it exists:* AI systems are non-deterministic; without tracing, debugging a failed workflow is impossible.
    *   *Benefits:* Provides an "Execution Tracer" UI where users can audit exactly why a decision was made, what parameters were passed, and what the external API returned.
    *   *Tradeoffs:* High storage overhead for trace data.

### 6.6 Plugin Architecture & Integration

*   **Integration Architecture:** Plugins (Nodes) are strictly isolated from the core engine. They define a strict input schema, an output schema, and an execution handler.
    *   *Why it exists:* To allow rapid scaling of supported integrations without bloating the core engine.
*   **MCP Integration (Future):** Moving towards adopting the Model Context Protocol (MCP) to dynamically ingest external capabilities.
    *   *Benefits:* Drastically reduces the engineering burden of maintaining hundreds of custom API integrations by standardizing how the AI discovers and interacts with tools.

### 6.7 Database Architecture & Caching

*   **Database Architecture:** PostgreSQL serves as the source of truth for relational metadata (users, workflow definitions, RBAC).
*   **Caching Strategy:** Redis is utilized for high-speed semantic caching and rate-limiting.
    *   *Why it exists:* To prevent redundant LLM calls for identical intents, saving cost and reducing latency.

### 6.8 Deployment Architecture

*   **Scalability:** The Control Plane (API) and Data Plane (Workers) scale independently. The message bus handles backpressure during execution spikes.
*   **Local vs Cloud Execution:** The architecture supports a hybrid model. The Control Plane resides in the cloud, while Execution Workers can be deployed locally within an enterprise VPC to interact with secure internal systems.
    *   *Why it exists:* To satisfy strict enterprise compliance requirements regarding data residency and network security.

## 7. Future Enhancements

While the current architecture focuses on robust, durable execution of deterministic DAGs, the platform is designed to support the following advanced capabilities:

*   **Multi-Agent Coordination:** Transitioning from single-planner execution to multi-agent negotiation, where a "Reviewer Agent" can critique a "Generator Agent's" plan before execution.
*   **Self-Healing Workflows:** Implementing adaptive retry mechanisms where, upon an API failure, a localized AI agent reads the error response and dynamically patches the payload without human intervention.
*   **Formal Semantic IR:** Fully replacing the JSON DSL with a typed Semantic Intermediate Representation, allowing for mathematical verification of workflow paths.
*   **Speculative Execution:** For high-latency branches (like waiting for human approval), the engine may speculatively execute probable downstream paths in an isolated sandbox to reduce apparent latency.
