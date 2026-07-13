/**
 * AutoFlow AI X — Frontend Validation Pipeline  (Sprint 3.5, Goal 6 frontend)
 * =============================================================================
 * A composable, layered validation pipeline for DSL edits in the browser.
 *
 * Mirrors the backend ValidationPipeline for immediate field-level feedback
 * before the user hits Save. The backend still runs the authoritative check
 * at persist time — this is defensive UX only.
 *
 * Stages (in order):
 *   1. UIValidationStage     — required fields, type coercions, non-empty checks
 *   2. SchemaValidationStage — structural checks (nodes array, edges, IDs)
 *   3. BusinessRulesStage    — graph-level rules (no empty node IDs, no duplicate IDs)
 *
 * Usage:
 *   import { defaultPipeline } from '../utils/validationPipeline';
 *
 *   const result = defaultPipeline().run(dsl);
 *   if (!result.isValid) {
 *     console.error(result.errors);
 *   }
 *
 * @module validationPipeline
 */

// ─── Validation Context ────────────────────────────────────────────────────────

/**
 * ValidationContext — shared state flowing through each pipeline stage.
 *
 * @param {Object} rawInput  - The DSL dict to validate
 */
export class ValidationContext {
  constructor(rawInput) {
    /** @type {Object} */
    this.rawInput = rawInput;
    /** @type {string[]} */
    this.errors = [];
    /** @type {string[]} */
    this.warnings = [];
    /** @type {Object|null} */
    this.parsedDsl = null;
  }

  /** @returns {boolean} */
  get isValid() {
    return this.errors.length === 0;
  }

  addError(msg) {
    this.errors.push(msg);
  }

  addWarning(msg) {
    this.warnings.push(msg);
  }
}


// ─── Stage Interface ───────────────────────────────────────────────────────────

/**
 * Base class for validation stages.
 * Each stage receives the ValidationContext and mutates it.
 *
 * @abstract
 */
export class ValidationStage {
  /**
   * @param {ValidationContext} ctx
   */
  // eslint-disable-next-line no-unused-vars
  run(ctx) {
    throw new Error(`${this.constructor.name}.run() not implemented`);
  }
}


// ─── Stage 1: UI Validation ────────────────────────────────────────────────────

/**
 * UIValidationStage — field-level quick checks.
 * Verifies that the DSL is a non-null object with the minimum shape.
 */
export class UIValidationStage extends ValidationStage {
  run(ctx) {
    const dsl = ctx.rawInput;

    if (!dsl || typeof dsl !== 'object') {
      ctx.addError('DSL must be a non-null object.');
      return;
    }

    if (!dsl.id) {
      ctx.addWarning('DSL is missing an "id" field.');
    }

    if (!dsl.name || typeof dsl.name !== 'string' || dsl.name.trim() === '') {
      ctx.addWarning('Workflow name is missing or empty.');
    }

    ctx.parsedDsl = dsl; // pass through to next stage
  }
}


// ─── Stage 2: Schema Validation ───────────────────────────────────────────────

/**
 * SchemaValidationStage — structural checks.
 * Validates the nodes and edges arrays exist and have minimum shape.
 */
export class SchemaValidationStage extends ValidationStage {
  run(ctx) {
    if (!ctx.parsedDsl) return; // upstream stage already failed

    const { nodes, edges } = ctx.parsedDsl;

    if (!Array.isArray(nodes)) {
      ctx.addError('"nodes" must be an array.');
    } else {
      nodes.forEach((node, i) => {
        if (!node.id) {
          ctx.addError(`Node at index ${i} is missing an "id" field.`);
        }
        if (!node.node_type) {
          ctx.addWarning(`Node '${node.id || i}' is missing "node_type".`);
        }
      });
    }

    if (!Array.isArray(edges)) {
      ctx.addError('"edges" must be an array.');
    } else {
      edges.forEach((edge, i) => {
        if (!edge.source_id || !edge.target_id) {
          ctx.addError(
            `Edge at index ${i} is missing "source_id" or "target_id".`,
          );
        }
      });
    }
  }
}


// ─── Stage 3: Business Rules ───────────────────────────────────────────────────

/**
 * BusinessRulesStage — graph-level invariants.
 * Validates no duplicate node IDs, edge endpoints reference real nodes, etc.
 */
export class BusinessRulesStage extends ValidationStage {
  run(ctx) {
    if (!ctx.parsedDsl || !ctx.isValid) return; // don't cascade on structural failure

    const { nodes = [], edges = [] } = ctx.parsedDsl;
    const nodeIds = new Set();

    for (const node of nodes) {
      if (nodeIds.has(node.id)) {
        ctx.addError(`Duplicate node ID: '${node.id}'.`);
      }
      nodeIds.add(node.id);
    }

    for (const edge of edges) {
      if (edge.source_id && !nodeIds.has(edge.source_id)) {
        ctx.addWarning(
          `Edge source '${edge.source_id}' does not match any node ID.`,
        );
      }
      if (edge.target_id && !nodeIds.has(edge.target_id)) {
        ctx.addWarning(
          `Edge target '${edge.target_id}' does not match any node ID.`,
        );
      }
    }
  }
}


// ─── Pipeline ─────────────────────────────────────────────────────────────────

/**
 * ValidationPipeline — runs an ordered list of ValidationStages.
 *
 * @example
 * const result = new ValidationPipeline([
 *   new UIValidationStage(),
 *   new SchemaValidationStage(),
 *   new BusinessRulesStage(),
 * ]).run(dsl);
 */
export class ValidationPipeline {
  /**
   * @param {ValidationStage[]} stages
   */
  constructor(stages = []) {
    this._stages = stages;
  }

  /**
   * Run all stages in order and return the final ValidationContext.
   *
   * @param {Object} rawInput  - The DSL dict to validate
   * @returns {ValidationContext}
   */
  run(rawInput) {
    const ctx = new ValidationContext(rawInput);
    for (const stage of this._stages) {
      try {
        stage.run(ctx);
      } catch (err) {
        ctx.addError(`[${stage.constructor.name}] Unexpected error: ${err.message}`);
      }
    }
    return ctx;
  }
}


// ─── Default Pipeline Factory ──────────────────────────────────────────────────

/**
 * defaultPipeline — create a pipeline with all three production stages.
 * Call this once per validation cycle (no shared state between runs).
 *
 * @returns {ValidationPipeline}
 */
export function defaultPipeline() {
  return new ValidationPipeline([
    new UIValidationStage(),
    new SchemaValidationStage(),
    new BusinessRulesStage(),
  ]);
}
