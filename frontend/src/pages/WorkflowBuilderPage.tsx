import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
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
  useWorkflowPersistence,
  type PersistedWorkflow,
} from '@/components/workflow-builder/lib/useWorkflowPersistence';
import type { ComponentFlowNode } from '@/components/workflow-builder/types';

export default function WorkflowBuilderPage() {
  const { id } = useParams<{ id: string }>();
  const [workflowName, setWorkflowName] = useState(DEFAULT_WORKFLOW_NAME);
  const [nodes, setNodes, onNodesChange] = useNodesState<ComponentFlowNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [savedAt, setSavedAt] = useState<string | null>(null);

  const { load, save } = useWorkflowPersistence();

  // StrictMode runs effects twice in dev; without this the restore toast fires twice
  const restoredId = useRef<string | null>(null);

  useEffect(() => {
    if (!id || restoredId.current === id) return;
    restoredId.current = id;

    const result = load(id);
    // no record yet - this id was just minted by the overview's "New Workflow"
    if (!result) return;

    const { workflow, droppedNodeCount, droppedEdgeCount } = result;
    setWorkflowName(workflow.workflowName);
    setNodes(workflow.nodes);
    setEdges(workflow.edges);
    setSavedAt(workflow.savedAt);

    toast.info(`Restored "${workflow.workflowName}".`);

    if (droppedNodeCount > 0 || droppedEdgeCount > 0) {
      toast.warning('Some components could not be restored - they may have been removed.');
    }
  }, [id, load, setNodes, setEdges]);

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
    if (!id) return;

    const workflow: PersistedWorkflow = {
      id,
      workflowName: workflowName.trim() || DEFAULT_WORKFLOW_NAME,
      nodes,
      edges,
      nodeCount: nodes.length,
      savedAt: new Date().toISOString(),
    };

    if (!save(workflow)) {
      toast.error('Could not save - browser storage is full.');
      return;
    }

    setWorkflowName(workflow.workflowName);
    setSavedAt(workflow.savedAt);
    toast.success('Workflow saved.');
  }, [id, workflowName, nodes, edges, save]);

  return (
    // required for WorkflowCanvas's useReactFlow()/screenToFlowPosition call
    <ReactFlowProvider>
      <div className="flex h-full flex-col">
        <WorkflowTopBar
          workflowName={workflowName}
          onWorkflowNameChange={setWorkflowName}
          onSave={handleSave}
          savedAt={savedAt}
        />
        {/* min-h-0: without it the flex child refuses to shrink and the canvas
            overflows past the bottom of the viewport */}
        <div className="flex min-h-0 flex-1">
          <WorkflowSidebar outputStack={outputStack} />
          <WorkflowCanvas
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onAddNode={onAddNode}
          />
        </div>
      </div>
    </ReactFlowProvider>
  );
}
