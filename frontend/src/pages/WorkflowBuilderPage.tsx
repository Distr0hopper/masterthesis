import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ReactFlowProvider,
  addEdge,
  useEdgesState,
  useNodesState,
  type Connection,
  type Edge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { toast } from 'sonner';
import { useQueryClient } from '@tanstack/react-query';
import { WorkflowCanvas } from '@/components/workflow-builder/WorkflowCanvas';
import { CanvasValidationDialog } from '@/components/workflow-builder/CanvasValidationDialog';
import { WorkflowInspector } from '@/components/workflow-builder/WorkflowInspector';
import { WorkflowSidebar } from '@/components/workflow-builder/WorkflowSidebar';
import { WorkflowTopBar } from '@/components/workflow-builder/WorkflowTopBar';
import {
  checkConnection,
  connectionKey,
  useConnectionChecks,
  type ConnectionCheckDto,
  type ConnectionDto,
} from '@/api/compatibility';
import {
  DEFAULT_WORKFLOW_NAME,
  parseCanvasState,
  serializeCanvasState,
} from '@/components/workflow-builder/lib/canvasState';
import {
  validateCanvas,
  type ValidationError,
} from '@/components/workflow-builder/lib/canvasValidation';
import { downloadBlob } from '@/lib/download';
import {
  useCreateDraft,
  useExportDraft,
  useExportDraftInputs,
  useSyncDraftToMyWorkflows,
  useUpdateDraft,
  useWorkflowDraft,
} from '@/api/workflow-drafts';
import type { ComponentEdgeData, ComponentFlowNode } from '@/components/workflow-builder/types';
import { getErrorMessage } from '@/lib/errors';
import { ROUTES } from '@/lib/routes';

export default function WorkflowBuilderPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  // `/builder/new` has no draft behind it yet - the first Save creates one
  const isNew = id === undefined;
  const draftId = id ?? '';

  const [workflowName, setWorkflowName] = useState(DEFAULT_WORKFLOW_NAME);
  const [nodes, setNodes, onNodesChange] = useNodesState<ComponentFlowNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  const { data: draft, isLoading, isError } = useWorkflowDraft(draftId, !isNew);
  const { mutateAsync: createDraft, isPending: isCreating } = useCreateDraft();
  const { mutateAsync: updateDraft, isPending: isUpdating } = useUpdateDraft(draftId);
  const { mutateAsync: exportDraft, isPending: isExporting } = useExportDraft();
  const { mutateAsync: exportDraftInputs, isPending: isExportingInputs } = useExportDraftInputs();
  const { mutateAsync: syncToMyWorkflows } = useSyncDraftToMyWorkflows();

  // components the backend reports as deleted - refreshed from every draft response, so a
  // component deleted while the builder is open is flagged on the next save
  const [missingComponentIds, setMissingComponentIds] = useState<ReadonlySet<string>>(() => new Set());

  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([]);
  const [validationOpen, setValidationOpen] = useState(false);

  // Restore once per draft. The query is staleTime: Infinity, but a re-render must not
  // stomp canvas edits made since the fetch resolved. This id also gates the canvas mount
  // (`restored` below): the canvas only renders once the restored graph is in state.
  const [restoredDraftId, setRestoredDraftId] = useState<string | null>(null);
  const restored = isNew || restoredDraftId === draftId;

  useEffect(() => {
    if (!draft || restoredDraftId === draft.id) return;
    setRestoredDraftId(draft.id);

    setWorkflowName(draft.name);

    const parsed = parseCanvasState(draft.canvasState);
    if (!parsed) {
      toast.error('This workflow’s canvas could not be read.');
      return;
    }

    setNodes(parsed.nodes);
    setEdges(parsed.edges);

    const missing = new Set(draft.missingComponentIds);
    setMissingComponentIds(missing);
    const missingLabels = [
      ...new Set(parsed.nodes.filter((n) => missing.has(n.data.componentId)).map((n) => n.data.label)),
    ];
    if (missingLabels.length > 0) {
      toast.error(
        `${missingLabels.length} component${missingLabels.length === 1 ? ' on this canvas was' : 's on this canvas were'} deleted from the repository.`,
        {
          description: `${missingLabels.join(', ')} - remove or replace ${missingLabels.length === 1 ? 'it' : 'them'} before saving or exporting.`,
          duration: 10_000,
        },
      );
    }

    if (parsed.droppedNodeCount > 0 || parsed.droppedEdgeCount > 0) {
      toast.warning('Some components or connections could not be restored - they may have been removed.');
    }
  }, [draft, restoredDraftId, setNodes, setEdges]);

  // the nodes as rendered: deleted components flagged for ComponentNode. Derived rather
  // than stored (like checkedEdges), so the flag never ends up in a saved draft; only the
  // affected nodes get new objects, the rest keep their identity
  const displayNodes = useMemo(
    () =>
      missingComponentIds.size === 0
        ? nodes
        : nodes.map((n) => (missingComponentIds.has(n.data.componentId) ? { ...n, data: { ...n.data, missing: true } } : n)),
    [nodes, missingComponentIds],
  );
  const hasMissingNodes = displayNodes.some((n) => n.data.missing);

  // the palette ranks against every canvas node's component, most recently added first.
  // Joined into a key so dragging a node (a new `nodes` array, same components) doesn't
  // hand the sidebar a new array and re-rank
  const rankAgainstKey = nodes
    .map((n) => n.data.componentId)
    .filter((componentId) => !missingComponentIds.has(componentId))
    .reverse()
    .join(',');
  const rankAgainst = useMemo(() => (rankAgainstKey ? rankAgainstKey.split(',') : []), [rankAgainstKey]);

  const queryClient = useQueryClient();

  /** The edge as the backend addresses it - null when a node or port is gone from the canvas. */
  const toConnectionDto = useCallback(
    (edge: Pick<Edge, 'source' | 'target' | 'sourceHandle' | 'targetHandle'>): ConnectionDto | null => {
      const source = nodes.find((n) => n.id === edge.source);
      const target = nodes.find((n) => n.id === edge.target);
      if (!source || !target || !edge.sourceHandle || !edge.targetHandle) return null;
      return {
        sourceComponentId: source.data.componentId,
        sourcePort: edge.sourceHandle,
        targetComponentId: target.data.componentId,
        targetPort: edge.targetHandle,
      };
    },
    [nodes],
  );

  const onConnect = useCallback(
    async (connection: Connection) => {
      const dto = toConnectionDto(connection);
      if (!dto) return;

      const deleted = [dto.sourceComponentId, dto.targetComponentId].some((c) => missingComponentIds.has(c));
      if (deleted) {
        toast.error('This component was deleted from the repository - it cannot be connected.');
        return;
      }

      const inputTaken = (candidates: Edge[]) =>
        candidates.some((e) => e.target === connection.target && e.targetHandle === connection.targetHandle);
      if (inputTaken(edges)) {
        toast.error(`"${dto.targetPort}" is already connected`);
        return;
      }

      // the backend decides - drawing the edge waits for it, since "incompatible" must block
      let check: ConnectionCheckDto;
      try {
        check = await checkConnection(queryClient, dto);
      } catch {
        toast.warning('Connected, but the connection could not be checked right now.');
        setEdges((prev) => (inputTaken(prev) ? prev : addEdge(connection, prev)));
        return;
      }
      if (check.status === 'incompatible') {
        toast.error(check.message ?? 'These ports are incompatible.');
        return;
      }
      if (check.status === 'unverified' && check.message) {
        toast.warning(`Connected, but not verified - ${check.message}`);
      }

      // re-checked against the latest edges: the await above leaves a window for another connect
      setEdges((prev) => (inputTaken(prev) ? prev : addEdge(connection, prev)));
    },
    [toConnectionDto, edges, missingComponentIds, queryClient, setEdges],
  );

  // every edge's verdict, including edges restored from a draft - in one request
  const edgeConnections = useMemo(
    () => edges.map(toConnectionDto).filter((c): c is ConnectionDto => c !== null),
    [edges, toConnectionDto],
  );
  const edgeChecks = useConnectionChecks(edgeConnections);

  // the verdict rides on each edge's data for ComponentEdge to render - derived on every
  // change rather than stored, so it never ends up in a saved draft
  const checkedEdges = useMemo(
    () =>
      edges.map((edge): Edge<ComponentEdgeData> => {
        const dto = toConnectionDto(edge);
        const check = dto ? edgeChecks.get(connectionKey(dto)) : undefined;
        return { ...edge, data: { ...edge.data, check } };
      }),
    [edges, toConnectionDto, edgeChecks],
  );

  const onAddNode = useCallback(
    (node: ComponentFlowNode) => setNodes((prev) => [...prev, node]),
    [setNodes],
  );

  const selectedNode = useMemo(() => displayNodes.find((n) => n.selected) ?? null, [displayNodes]);

  const onParameterChange = useCallback(
    (nodeId: string, parameterName: string, value: string | undefined) => {
      setNodes((prev) =>
        prev.map((node) => {
          if (node.id !== nodeId) return node;

          const parameterValues = { ...node.data.parameterValues };
          if (value === undefined) delete parameterValues[parameterName];
          else parameterValues[parameterName] = value;

          return { ...node, data: { ...node.data, parameterValues } };
        }),
      );
    },
    [setNodes],
  );

  /**
   * Write the current canvas to the server and resolve with the draft id it now lives
   * under. Export reads the draft back from the DB, so it has to go through this first -
   * otherwise an edited-but-unsaved name or canvas is silently exported at its last-saved
   * value. Also resolves with the canvas's deleted components as the server sees them now.
   */
  const persist = useCallback(async (): Promise<{ id: string; missingComponentIds: string[] }> => {
    const name = workflowName.trim() || DEFAULT_WORKFLOW_NAME;
    setWorkflowName(name);

    const dto = {
      name,
      canvasState: serializeCanvasState(nodes, edges),
      nodeCount: nodes.length,
    };

    if (isNew) {
      const created = await createDraft(dto);
      setRestoredDraftId(created.id);
      setMissingComponentIds(new Set(created.missingComponentIds));
      navigate(ROUTES.builderWorkflow(created.id), { replace: true });
      return { id: created.id, missingComponentIds: created.missingComponentIds };
    }

    const updated = await updateDraft(dto);
    setMissingComponentIds(new Set(updated.missingComponentIds));
    return { id: draftId, missingComponentIds: updated.missingComponentIds };
  }, [isNew, draftId, workflowName, nodes, edges, createDraft, updateDraft, navigate]);

  const handleSave = useCallback(async () => {
    let saved: { id: string; missingComponentIds: string[] };
    try {
      saved = await persist();
    } catch (error) {
      toast.error(getErrorMessage(error, 'Could not save this workflow.'));
      return;
    }

    // syncing would only fail on the deleted components - say so instead of a generic error
    const missing = new Set(saved.missingComponentIds);
    const missingLabels = [...new Set(nodes.filter((n) => missing.has(n.data.componentId)).map((n) => n.data.label))];
    if (missingLabels.length > 0) {
      toast.warning('Workflow saved, but not added to My Workflows yet.', {
        description: `Deleted component${missingLabels.length === 1 ? '' : 's'} on the canvas: ${missingLabels.join(', ')}. Remove or replace ${missingLabels.length === 1 ? 'it' : 'them'}, then save again.`,
      });
      return;
    }

    try {
      await syncToMyWorkflows(saved.id);
      toast.success('Saved to My Workflows.', {
        description: 'Publishing is done from the My Workflows page.',
        action: { label: 'My Workflows', onClick: () => navigate(ROUTES.myWorkflows) },
      });
    } catch (error) {
      toast.warning('Workflow saved, but not added to My Workflows yet.', {
        description: getErrorMessage(error, 'Finish the canvas, then save again.'),
      });
    }
  }, [persist, nodes, syncToMyWorkflows, navigate]);

  const runExport = useCallback(async () => {
    try {
      const { id } = await persist();
      const { blob, filename } = await exportDraft(id);
      downloadBlob(filename, blob);
      toast.success('Workflow exported.');
    } catch (error) {
      toast.error(getErrorMessage(error, 'Could not export this workflow.'));
    }
  }, [persist, exportDraft]);

  const guard = useCallback(
    (run: () => void) => {
      const errors = validateCanvas(nodes, edges, workflowName, missingComponentIds);
      if (errors.length === 0) {
        run();
        return;
      }
      setValidationErrors(errors);
      setValidationOpen(true);
    },
    [nodes, edges, workflowName, missingComponentIds],
  );

  const handleExport = useCallback(() => guard(() => void runExport()), [guard, runExport]);

  // no full validation dialog here: its main warning - "this input will become an input of the
  // whole workflow" - is exactly what this file is for. An empty canvas or a cycle is still
  // rejected by the backend and shown as a toast.
  const handleExportInputs = useCallback(async () => {
    if (hasMissingNodes) {
      // the only check worth the dialog here: the backend would reject the export anyway
      setValidationErrors(
        validateCanvas(nodes, edges, workflowName, missingComponentIds).filter((e) => e.type === 'missing_component'),
      );
      setValidationOpen(true);
      return;
    }
    try {
      const { id } = await persist();
      const { blob, filename } = await exportDraftInputs(id);
      downloadBlob(filename, blob);
      toast.success('inputs.yaml exported.');
    } catch (error) {
      toast.error(getErrorMessage(error, 'Could not export the inputs of this workflow.'));
    }
  }, [hasMissingNodes, nodes, edges, workflowName, missingComponentIds, persist, exportDraftInputs]);

  const handleProceedAnyway = useCallback(() => {
    setValidationOpen(false);
    void runExport();
  }, [runExport]);

  return (
    <ReactFlowProvider>
      <div className="flex h-full flex-col">
        <WorkflowTopBar
          workflowName={workflowName}
          onWorkflowNameChange={setWorkflowName}
          onSave={handleSave}
          isSaving={isCreating || isUpdating}
          onExport={handleExport}
          isExporting={isExporting}
          onExportInputs={() => void handleExportInputs()}
          isExportingInputs={isExportingInputs}
          updatedAt={draft?.updatedAt ?? null}
        />
        <div className="flex min-h-0 flex-1">
          <WorkflowSidebar rankAgainst={rankAgainst} />
          {isError ? (
            <div className="flex flex-1 items-center justify-center text-slate-500">
              This workflow could not be loaded.
            </div>
          ) : isLoading || !restored ? (
            <div className="flex flex-1 items-center justify-center text-slate-500">
              Loading workflow...
            </div>
          ) : (
            <WorkflowCanvas
              nodes={displayNodes}
              edges={checkedEdges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              onAddNode={onAddNode}
            />
          )}
          {selectedNode && (
            <WorkflowInspector node={selectedNode} onParameterChange={onParameterChange} />
          )}
        </div>
      </div>

      <CanvasValidationDialog
        open={validationOpen}
        onOpenChange={setValidationOpen}
        errors={validationErrors}
        onProceed={handleProceedAnyway}
      />
    </ReactFlowProvider>
  );
}
