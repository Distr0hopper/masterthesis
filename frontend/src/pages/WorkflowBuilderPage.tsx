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
import { WorkflowCanvas } from '@/components/workflow-builder/WorkflowCanvas';
import { CanvasValidationDialog } from '@/components/workflow-builder/CanvasValidationDialog';
import { WorkflowInspector } from '@/components/workflow-builder/WorkflowInspector';
import { WorkflowSidebar } from '@/components/workflow-builder/WorkflowSidebar';
import { WorkflowTopBar } from '@/components/workflow-builder/WorkflowTopBar';
import {
  arePortsCompatible,
  buildOutputStack,
  findPort,
} from '@/components/workflow-builder/lib/typeChecking';
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
  usePublishDraft,
  useUpdateDraft,
  useWorkflowDraft,
} from '@/api/workflow-drafts';
import type { ComponentFlowNode } from '@/components/workflow-builder/types';
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
  const { mutateAsync: publishDraft, isPending: isPublishing } = usePublishDraft();

  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([]);
  const [validationOpen, setValidationOpen] = useState(false);
  // which action the validation dialog is gating, so it can label its own button
  const [pendingAction, setPendingAction] = useState<'export' | 'publish'>('export');

  // Restore once per draft. The query is staleTime: Infinity, but a re-render must not
  // stomp canvas edits made since the fetch resolved. This id also gates the canvas mount
  // (`restored` below): the canvas only renders once the restored graph is in state, so
  // React Flow's own fitView frames it on first paint and no manual re-fit is needed.
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

    if (parsed.droppedNodeCount > 0 || parsed.droppedEdgeCount > 0) {
      toast.warning('Some components or connections could not be restored - they may have been removed.');
    }
  }, [draft, restoredDraftId, setNodes, setEdges]);

  // the sidebar ranks its palette against whatever the canvas can currently produce
  const outputStack = useMemo(() => buildOutputStack(nodes), [nodes]);

  const onConnect = useCallback(
    (connection: Connection) => {
      const source = nodes.find((n) => n.id === connection.source);
      const target = nodes.find((n) => n.id === connection.target);
      if (!source || !target) return;

      // handle ids are parameter names, so a connection names the exact ports it joins
      const sourcePort = findPort(source.data.parameters, connection.sourceHandle);
      const targetPort = findPort(target.data.parameters, connection.targetHandle);

      if (!arePortsCompatible(sourcePort, targetPort)) {
        toast.error(
          `Incompatible types - ${sourcePort?.cwlType ?? '?'} cannot feed ${targetPort?.cwlType ?? '?'}`,
        );
        return;
      }

      // a CWL step input takes exactly one source, so a second edge into the same input
      // would be ambiguous on export
      const inputTaken = edges.some(
        (e) => e.target === connection.target && e.targetHandle === connection.targetHandle,
      );
      if (inputTaken) {
        toast.error(`"${targetPort!.name}" is already connected`);
        return;
      }

      // edge styling comes from the canvas's defaultEdgeOptions, not repeated here
      setEdges((prev) => addEdge(connection, prev));
    },
    [nodes, edges, setEdges],
  );

  const onAddNode = useCallback(
    (node: ComponentFlowNode) => setNodes((prev) => [...prev, node]),
    [setNodes],
  );

  // React Flow owns selection state, so the inspector reads it off the nodes themselves
  const selectedNode = useMemo(() => nodes.find((n) => n.selected) ?? null, [nodes]);

  const onParameterChange = useCallback(
    (nodeId: string, parameterName: string, value: string | undefined) => {
      setNodes((prev) =>
        prev.map((node) => {
          if (node.id !== nodeId) return node;

          const parameterValues = { ...node.data.parameterValues };
          // undefined clears the override, restoring the component's own default
          if (value === undefined) delete parameterValues[parameterName];
          else parameterValues[parameterName] = value;

          // new node and data objects - React Flow diffs by reference
          return { ...node, data: { ...node.data, parameterValues } };
        }),
      );
    },
    [setNodes],
  );

  /**
   * Write the current canvas to the server and resolve with the draft id it now lives
   * under. Export and publish both read the draft back from the DB, so they have to go
   * through this first - otherwise an edited-but-unsaved name or canvas is silently
   * exported at its last-saved value.
   */
  const persist = useCallback(async (): Promise<string> => {
    const name = workflowName.trim() || DEFAULT_WORKFLOW_NAME;
    setWorkflowName(name);

    const dto = {
      name,
      canvasState: serializeCanvasState(nodes, edges),
      nodeCount: nodes.length,
    };

    if (isNew) {
      const created = await createDraft(dto);
      // mark this id restored: keeps the canvas mounted (no loader flash) and stops the
      // restore effect from stomping the graph the user just built, once the URL flips to
      // /builder/:id below
      setRestoredDraftId(created.id);
      // replace, so Back does not return to /builder/new and create a second draft
      navigate(ROUTES.builderWorkflow(created.id), { replace: true });
      return created.id;
    }

    await updateDraft(dto);
    return draftId;
  }, [isNew, draftId, workflowName, nodes, edges, createDraft, updateDraft, navigate]);

  const handleSave = useCallback(async () => {
    try {
      await persist();
      toast.success('Workflow saved.');
    } catch (error) {
      toast.error(getErrorMessage(error, 'Could not save this workflow.'));
    }
  }, [persist]);

  const runExport = useCallback(async () => {
    try {
      // saving first guarantees the archive reflects the name and canvas on screen
      const id = await persist();
      const { blob, filename } = await exportDraft(id);
      downloadBlob(filename, blob);
      toast.success('Workflow exported.');
    } catch (error) {
      toast.error(getErrorMessage(error, 'Could not export this workflow.'));
    }
  }, [persist, exportDraft]);

  const runPublish = useCallback(async () => {
    try {
      // same reason as export: publish reads the draft back from the DB
      const id = await persist();
      const published = await publishDraft(id);
      toast.success(`Published "${published.name}" with ${published.stepCount} step(s).`, {
        action: {
          label: 'View',
          onClick: () => navigate(ROUTES.workflowDetail(published.workflowId)),
        },
      });
    } catch (error) {
      toast.error(getErrorMessage(error, 'Could not publish this workflow.'));
    }
  }, [persist, publishDraft, navigate]);

  // both actions gate on the same canvas validation; only the wording differs
  const guard = useCallback(
    (action: 'export' | 'publish', run: () => void) => {
      const errors = validateCanvas(nodes, edges, workflowName);
      if (errors.length === 0) {
        run();
        return;
      }
      setValidationErrors(errors);
      setPendingAction(action);
      setValidationOpen(true);
    },
    [nodes, edges, workflowName],
  );

  const handleExport = useCallback(() => guard('export', () => void runExport()), [guard, runExport]);
  const handlePublish = useCallback(() => guard('publish', () => void runPublish()), [guard, runPublish]);

  const handleProceedAnyway = useCallback(() => {
    setValidationOpen(false);
    if (pendingAction === 'publish') void runPublish();
    else void runExport();
  }, [pendingAction, runExport, runPublish]);

  return (
    // required for WorkflowCanvas's useReactFlow()/screenToFlowPosition call
    <ReactFlowProvider>
      <div className="flex h-full flex-col">
        <WorkflowTopBar
          workflowName={workflowName}
          onWorkflowNameChange={setWorkflowName}
          onSave={handleSave}
          isSaving={isCreating || isUpdating}
          onExport={handleExport}
          isExporting={isExporting}
          onPublish={handlePublish}
          isPublishing={isPublishing}
          updatedAt={draft?.updatedAt ?? null}
        />
        {/* min-h-0: without it the flex child refuses to shrink and the canvas
            overflows past the bottom of the viewport */}
        <div className="flex min-h-0 flex-1">
          <WorkflowSidebar outputStack={outputStack} />
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
              nodes={nodes}
              edges={edges}
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
        action={pendingAction}
        onProceed={handleProceedAnyway}
      />
    </ReactFlowProvider>
  );
}
