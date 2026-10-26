import { useCallback, useEffect, useMemo, useState } from 'react';
import { useBlocker, useNavigate, useParams } from 'react-router-dom';
import { ReactFlowProvider, addEdge, useEdgesState, useNodesState, type Connection, type Edge } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { toast } from 'sonner';
import { useQueryClient } from '@tanstack/react-query';
import { CanvasNotices } from '@/components/workflow-builder/CanvasNotices';
import { WorkflowCanvas } from '@/components/workflow-builder/WorkflowCanvas';
import { CanvasValidationDialog } from '@/components/workflow-builder/CanvasValidationDialog';
import { UnsavedChangesDialog } from '@/components/workflow-builder/UnsavedChangesDialog';
import { WorkflowInspector } from '@/components/workflow-builder/WorkflowInspector';
import { WorkflowSidebar } from '@/components/workflow-builder/WorkflowSidebar';
import { WorkflowTopBar } from '@/components/workflow-builder/WorkflowTopBar';
import { BuilderNeedsDesktop } from '@/components/workflow-builder/BuilderNeedsDesktop';
import {
  checkConnection,
  connectionKey,
  useConnectionChecks,
  type ConnectionCheckDto,
  type ConnectionDto,
} from '@/api/compatibility';
import {
  DEFAULT_WORKFLOW_NAME,
  canvasFingerprint,
  parseCanvasState,
  serializeCanvasState,
} from '@/components/workflow-builder/lib/canvasState';
import { validateCanvas, type ValidationError } from '@/components/workflow-builder/lib/canvasValidation';
import { downloadBlob } from '@/lib/download';
import { useMediaQuery } from '@/lib/useMediaQuery';
import {
  useCreateDraft,
  useExportDraft,
  useExportDraftInputs,
  useSyncDraftToMyComponents,
  useUpdateDraft,
  useWorkflowDraft,
} from '@/api/workflow-drafts';
import type { ComponentEdgeData, ComponentFlowNode } from '@/components/workflow-builder/types';
import { getErrorMessage } from '@/lib/errors';
import { ROUTES } from '@/lib/routes';

export default function WorkflowBuilderPage() {
  // Tailwind's md breakpoint - below it the builder isn't mounted at all, so neither its
  // queries nor its unsaved-changes blocker run for a page that can't be used
  const isWideEnough = useMediaQuery('(min-width: 768px)');
  return isWideEnough ? <WorkflowBuilder /> : <BuilderNeedsDesktop />;
}

function WorkflowBuilder() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  // `/builder/new` has no draft behind it yet - the first Save creates one
  const isNew = id === undefined;
  const draftId = id ?? '';

  const [workflowName, setWorkflowName] = useState(DEFAULT_WORKFLOW_NAME);
  const [nodes, setNodes, onNodesChange] = useNodesState<ComponentFlowNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  const { data: draft, isLoading, isFetching, isError } = useWorkflowDraft(draftId, !isNew);
  const { mutateAsync: createDraft, isPending: isCreating } = useCreateDraft();
  const { mutateAsync: updateDraft, isPending: isUpdating } = useUpdateDraft(draftId);
  const { mutateAsync: exportDraft, isPending: isExporting } = useExportDraft();
  const { mutateAsync: exportDraftInputs, isPending: isExportingInputs } = useExportDraftInputs();
  const { mutateAsync: syncToMyComponents } = useSyncDraftToMyComponents();

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

  // what restoring found wrong with the saved canvas - rendered by CanvasNotices
  const [restoreReport, setRestoreReport] = useState({ unreadable: false, dropped: false });

  // the canvas as the server last stored it - set on restore and after every persist; an
  // empty canvas counts as saved, so opening /builder/new and leaving again asks nothing
  const [savedFingerprint, setSavedFingerprint] = useState<string | null>(() =>
    isNew ? canvasFingerprint(DEFAULT_WORKFLOW_NAME, [], []) : null,
  );

  useEffect(() => {
    // waits for the fetch on open, not the cached copy from the last visit
    if (!draft || isFetching || restoredDraftId === draft.id) return;
    setRestoredDraftId(draft.id);

    setWorkflowName(draft.name);

    const parsed = parseCanvasState(draft.canvasState);
    if (!parsed) {
      setSavedFingerprint(canvasFingerprint(draft.name, [], []));
      setRestoreReport({ unreadable: true, dropped: false });
      return;
    }

    setSavedFingerprint(canvasFingerprint(draft.name, parsed.nodes, parsed.edges));
    setNodes(parsed.nodes);
    setEdges(parsed.edges);
    setMissingComponentIds(new Set(draft.missingComponentIds));
    setRestoreReport({ unreadable: false, dropped: parsed.droppedNodeCount > 0 || parsed.droppedEdgeCount > 0 });
  }, [draft, isFetching, restoredDraftId, setNodes, setEdges]);

  // the nodes as rendered: deleted components flagged for ComponentNode. Derived rather
  // than stored (like checkedEdges), so the flag never ends up in a saved draft; only the
  // affected nodes get new objects, the rest keep their identity
  const displayNodes = useMemo(
    () =>
      missingComponentIds.size === 0
        ? nodes
        : nodes.map((n) =>
            missingComponentIds.has(n.data.componentId) ? { ...n, data: { ...n.data, missing: true } } : n,
          ),
    [nodes, missingComponentIds],
  );

  // the deleted components still on the canvas - the notice goes once the last is replaced
  const missingLabels = useMemo(
    () => [...new Set(displayNodes.filter((n) => n.data.missing).map((n) => n.data.label))],
    [displayNodes],
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

  const onAddNode = useCallback((node: ComponentFlowNode) => setNodes((prev) => [...prev, node]), [setNodes]);

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
    // what this request stores - edits made while it is in flight still count as unsaved
    const fingerprint = canvasFingerprint(name, nodes, edges);

    if (isNew) {
      const created = await createDraft(dto);
      setRestoredDraftId(created.id);
      setSavedFingerprint(fingerprint);
      setMissingComponentIds(new Set(created.missingComponentIds));
      // flagged for the blocker: this render still sees the canvas as unsaved
      navigate(ROUTES.builderWorkflow(created.id), { replace: true, state: { saved: true } });
      return { id: created.id, missingComponentIds: created.missingComponentIds };
    }

    const updated = await updateDraft(dto);
    setSavedFingerprint(fingerprint);
    setMissingComponentIds(new Set(updated.missingComponentIds));
    return { id: draftId, missingComponentIds: updated.missingComponentIds };
  }, [isNew, draftId, workflowName, nodes, edges, createDraft, updateDraft, navigate]);

  // why the last Save couldn't reach My Components - shown above the canvas until one does
  const [notSynced, setNotSynced] = useState<string | null>(null);

  /** Resolves whether the canvas is stored now - syncing to My Components may still have failed. */
  const handleSave = useCallback(async (): Promise<boolean> => {
    let saved: { id: string; missingComponentIds: string[] };
    try {
      saved = await persist();
    } catch (error) {
      toast.error(getErrorMessage(error, 'Could not save this workflow.'));
      return false;
    }

    // syncing would only fail on the deleted components - say so instead of a generic error
    const missing = new Set(saved.missingComponentIds);
    const missingLabels = [...new Set(nodes.filter((n) => missing.has(n.data.componentId)).map((n) => n.data.label))];
    if (missingLabels.length > 0) {
      // the deleted components already have their own notice - this one says what it costs
      setNotSynced(`replace the deleted component${missingLabels.length === 1 ? '' : 's'}, then save again.`);
      toast.success('Workflow saved.');
      return true;
    }

    try {
      const synced = await syncToMyComponents(saved.id);
      setNotSynced(null);
      toast.success(`Saved - v${synced.version} in My Components is up to date.`);
    } catch (error) {
      setNotSynced(getErrorMessage(error, 'finish the canvas, then save again.'));
      toast.success('Workflow saved.');
    }
    return true;
  }, [persist, nodes, syncToMyComponents]);

  // compared on every render - cheap next to what React Flow does per frame
  const isDirty =
    restored && savedFingerprint !== null && canvasFingerprint(workflowName, nodes, edges) !== savedFingerprint;

  // leaving within the app: asked in our own dialog, with saving as one of the answers
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      isDirty &&
      currentLocation.pathname !== nextLocation.pathname &&
      !(nextLocation.state as { saved?: boolean } | null)?.saved,
  );
  const [isSavingToLeave, setIsSavingToLeave] = useState(false);
  const saveAndLeave = useCallback(async () => {
    setIsSavingToLeave(true);
    const saved = await handleSave();
    setIsSavingToLeave(false);
    if (saved) blocker.proceed?.();
    else blocker.reset?.();
  }, [handleSave, blocker]);

  // closing the tab or reloading: only the browser's own prompt can stop that
  useEffect(() => {
    if (!isDirty) return;
    const warn = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [isDirty]);

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
          onSave={() => void handleSave()}
          isSaving={isCreating || isUpdating}
          onExport={handleExport}
          isExporting={isExporting}
          onExportInputs={() => void handleExportInputs()}
          isExportingInputs={isExportingInputs}
          updatedAt={draft?.updatedAt ?? null}
          isDirty={isDirty}
          linkedWorkflow={draft?.linkedWorkflow ?? null}
        />
        <div className="flex min-h-0 flex-1">
          <WorkflowSidebar rankAgainst={rankAgainst} nestableIn={draft?.linkedWorkflow?.id} />
          {isError ? (
            <div className="flex flex-1 items-center justify-center text-slate-500">
              This workflow could not be loaded.
            </div>
          ) : isLoading || !restored ? (
            <div className="flex flex-1 items-center justify-center text-slate-500">Loading workflow...</div>
          ) : (
            <div className="flex min-w-0 flex-1 flex-col">
              <CanvasNotices
                missingLabels={missingLabels}
                unreadable={restoreReport.unreadable}
                dropped={restoreReport.dropped}
                onDismissDropped={() => setRestoreReport((report) => ({ ...report, dropped: false }))}
                notSynced={notSynced}
              />
              <div className="flex min-h-0 flex-1">
                <WorkflowCanvas
                  nodes={displayNodes}
                  edges={checkedEdges}
                  onNodesChange={onNodesChange}
                  onEdgesChange={onEdgesChange}
                  onConnect={onConnect}
                  onAddNode={onAddNode}
                />
              </div>
            </div>
          )}
          {selectedNode && <WorkflowInspector node={selectedNode} onParameterChange={onParameterChange} />}
        </div>
      </div>

      <CanvasValidationDialog
        open={validationOpen}
        onOpenChange={setValidationOpen}
        errors={validationErrors}
        onProceed={handleProceedAnyway}
      />
      <UnsavedChangesDialog
        open={blocker.state === 'blocked'}
        onStay={() => blocker.reset?.()}
        onLeave={() => blocker.proceed?.()}
        onSaveAndLeave={() => void saveAndLeave()}
        isSaving={isSavingToLeave}
      />
    </ReactFlowProvider>
  );
}
