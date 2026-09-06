import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
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
import { WorkflowSidebar } from '@/components/workflow-builder/WorkflowSidebar';
import { WorkflowTopBar } from '@/components/workflow-builder/WorkflowTopBar';
import {
  areParametersCompatible,
  buildOutputStack,
} from '@/components/workflow-builder/lib/typeChecking';
import {
  DEFAULT_WORKFLOW_NAME,
  parseCanvasState,
  serializeCanvasState,
} from '@/components/workflow-builder/lib/canvasState';
import { useCreateDraft, useUpdateDraft, useWorkflowDraft } from '@/api/workflow-drafts';
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

  const { data: draft, isLoading } = useWorkflowDraft(draftId, !isNew);
  const { mutate: createDraft, isPending: isCreating } = useCreateDraft();
  const { mutate: updateDraft, isPending: isUpdating } = useUpdateDraft(draftId);

  // restore once per draft - the query is staleTime: Infinity, but a re-render must not
  // stomp on canvas edits the user has made since the fetch resolved
  const restoredId = useRef<string | null>(null);

  useEffect(() => {
    if (!draft || restoredId.current === draft.id) return;
    restoredId.current = draft.id;

    setWorkflowName(draft.name);

    const parsed = parseCanvasState(draft.canvasState);
    if (!parsed) {
      toast.error('This workflow’s canvas could not be read.');
      return;
    }

    setNodes(parsed.nodes);
    setEdges(parsed.edges);

    if (parsed.droppedNodeCount > 0 || parsed.droppedEdgeCount > 0) {
      toast.warning('Some components could not be restored - they may have been removed.');
    }
  }, [draft, setNodes, setEdges]);

  // the sidebar ranks its palette against whatever the canvas can currently produce
  const outputStack = useMemo(() => buildOutputStack(nodes), [nodes]);

  const onConnect = useCallback(
    (connection: Connection) => {
      const source = nodes.find((n) => n.id === connection.source);
      const target = nodes.find((n) => n.id === connection.target);
      if (!source || !target) return;

      if (!areParametersCompatible(source.data.parameters, target.data.parameters)) {
        toast.error('Incompatible types - cannot connect these components');
        return;
      }

      // edge styling comes from the canvas's defaultEdgeOptions, not repeated here
      setEdges((prev) => addEdge(connection, prev));
    },
    [nodes, setEdges],
  );

  const onAddNode = useCallback(
    (node: ComponentFlowNode) => setNodes((prev) => [...prev, node]),
    [setNodes],
  );

  const handleSave = useCallback(() => {
    const name = workflowName.trim() || DEFAULT_WORKFLOW_NAME;
    setWorkflowName(name);

    const dto = {
      name,
      canvasState: serializeCanvasState(nodes, edges),
      nodeCount: nodes.length,
    };

    const onError = (error: unknown) =>
      toast.error(getErrorMessage(error, 'Could not save this workflow.'));

    if (isNew) {
      createDraft(dto, {
        onSuccess: (created) => {
          // replace, so Back does not return to /builder/new and create a second draft
          restoredId.current = created.id;
          navigate(ROUTES.builderWorkflow(created.id), { replace: true });
          toast.success('Workflow saved.');
        },
        onError,
      });
      return;
    }

    updateDraft(dto, {
      onSuccess: () => toast.success('Workflow saved.'),
      onError,
    });
  }, [isNew, workflowName, nodes, edges, createDraft, updateDraft, navigate]);

  return (
    // required for WorkflowCanvas's useReactFlow()/screenToFlowPosition call
    <ReactFlowProvider>
      <div className="flex h-full flex-col">
        <WorkflowTopBar
          workflowName={workflowName}
          onWorkflowNameChange={setWorkflowName}
          onSave={handleSave}
          isSaving={isCreating || isUpdating}
          updatedAt={draft?.updatedAt ?? null}
        />
        {/* min-h-0: without it the flex child refuses to shrink and the canvas
            overflows past the bottom of the viewport */}
        <div className="flex min-h-0 flex-1">
          <WorkflowSidebar outputStack={outputStack} />
          {isLoading ? (
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
        </div>
      </div>
    </ReactFlowProvider>
  );
}
