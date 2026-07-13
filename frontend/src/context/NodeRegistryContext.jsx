/**
 * AutoFlow AI X — NodeRegistryContext  (Sprint 3.5, Goal 7)
 * ===========================================================
 * Provides the NodeRegistry lookup (list of NodeMetadataDTO) as React context,
 * eliminating repeated prop-drilling of `nodeTypes` through the component tree.
 *
 * WRAP LOCATION: Router level — wrapping WorkflowBuilderPage's <Route> so the
 * registry is fetched once per page load and shared across all Inspector,
 * AddStepPanel, and WorkflowNode components without refetching.
 *
 * Usage:
 *   // Provider (in App.jsx or a route wrapper):
 *   <NodeRegistryProvider>
 *     <WorkflowBuilderPage />
 *   </NodeRegistryProvider>
 *
 *   // Consumer (any child component):
 *   const { plugins, getPlugin, isLoading, error } = useNodeRegistry();
 *
 * @module NodeRegistryContext
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { workflowApi } from '../services/workflowApi';

// ─── Context definition ───────────────────────────────────────────────────────

const NodeRegistryContext = createContext(null);

// ─── Provider ─────────────────────────────────────────────────────────────────

/**
 * NodeRegistryProvider
 *
 * Fetches GET /workflows/node-types once on mount, caches the result,
 * and exposes it via NodeRegistryContext.
 *
 * @param {Object} props
 * @param {React.ReactNode} props.children
 */
export function NodeRegistryProvider({ children }) {
  const [plugins, setPlugins] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const fetchedRef = useRef(false); // guard against StrictMode double-invoke

  useEffect(() => {
    if (fetchedRef.current) return;
    fetchedRef.current = true;

    let cancelled = false;

    async function fetchRegistry() {
      try {
        setIsLoading(true);
        const data = await workflowApi.getNodeTypes();
        if (!cancelled) {
          setPlugins(data?.plugins ?? []);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          console.error('[NodeRegistryContext] Failed to load node types:', err);
          setError(err?.message ?? 'Failed to load node types');
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    fetchRegistry();
    return () => { cancelled = true; };
  }, []);

  /**
   * Look up a single plugin by service + operation.
   * Returns undefined if not found or still loading.
   *
   * @param {string} service    - e.g. 'gmail'
   * @param {string} operation  - e.g. 'send_email'
   * @returns {Object|undefined}
   */
  const getPlugin = useCallback(
    (service, operation) =>
      plugins.find(p => p.service === service && p.operation === operation),
    [plugins],
  );

  /**
   * Look up a plugin by its canonical 'service.operation' key.
   *
   * @param {string} key  - e.g. 'gmail.send_email'
   * @returns {Object|undefined}
   */
  const getPluginByKey = useCallback(
    (key) => {
      const [service, ...rest] = (key ?? '').split('.');
      const operation = rest.join('.');
      return getPlugin(service, operation);
    },
    [getPlugin],
  );

  /**
   * Look up a plugin that matches a given node DSL object.
   * Tries service + operation first, then falls back to node_type.
   *
   * @param {Object} node  - DSL node with {service?, operation?, node_type?}
   * @returns {Object|undefined}
   */
  const getPluginForNode = useCallback(
    (node) => {
      if (node?.service && node?.operation) {
        return getPlugin(node.service, node.operation);
      }
      // Fallback: match by node_type (imprecise — service.operation preferred)
      return plugins.find(p => p.node_type === node?.node_type);
    },
    [getPlugin, plugins],
  );

  const value = useMemo(
    () => ({
      plugins,
      isLoading,
      error,
      getPlugin,
      getPluginByKey,
      getPluginForNode,
    }),
    [plugins, isLoading, error, getPlugin, getPluginByKey, getPluginForNode],
  );

  return (
    <NodeRegistryContext.Provider value={value}>
      {children}
    </NodeRegistryContext.Provider>
  );
}

// ─── Consumer hook ────────────────────────────────────────────────────────────

/**
 * useNodeRegistry — consume the NodeRegistryContext.
 *
 * Must be used within a <NodeRegistryProvider> tree.
 * Throws if called outside the provider (fail-fast during development).
 *
 * @returns {{ plugins: Object[], isLoading: boolean, error: string|null, getPlugin: Function, getPluginByKey: Function, getPluginForNode: Function }}
 */
export function useNodeRegistry() {
  const ctx = useContext(NodeRegistryContext);
  if (ctx === null) {
    throw new Error(
      'useNodeRegistry() must be called inside a <NodeRegistryProvider>. ' +
      'Wrap your route or page component with <NodeRegistryProvider>.',
    );
  }
  return ctx;
}

export default NodeRegistryContext;
