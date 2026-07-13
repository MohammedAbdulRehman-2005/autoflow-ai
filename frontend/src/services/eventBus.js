/**
 * AutoFlow AI X — Frontend Event Bus  (RFC-001 §6)
 * ==================================================
 * Lightweight typed event emitter using `mitt`.
 *
 * Events emitted in Sprint 1:
 *   WorkflowPatched  { dsl, actor, reason }
 *   WorkflowSaved    { workflowId, name }
 *
 * Usage:
 *   import { eventBus } from '@/services/eventBus';
 *   eventBus.on('WorkflowPatched', ({ dsl }) => renderDsl(dsl));
 *   eventBus.emit('WorkflowPatched', { dsl, actor: 'ai', reason: 'AI planner' });
 *
 * Replaces the window.dispatchEvent('workflow-saved') hack.
 */

import mitt from 'mitt';

export const eventBus = mitt();
