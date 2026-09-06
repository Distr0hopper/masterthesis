import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
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
  formatRelativeTime,
  useWorkflowPersistence,
  type PersistedWorkflowState,
} from '@/components/workflow-builder/lib/useWorkflowPersistence';
import type { ComponentFlowNode } from '@/components/workflow-builder/types';

export default function WorkflowBuilderPage() {
  const [workflowName, setWorkflowName] = useState('');
  const [nodes, setNodes, onNodesChange] = useNodesState<ComponentFlowNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [savedAt, setSavedAt] = useState<string | null>(null);

  const { load, save, clear } = useWorkflowPersistence();

  // StrictMode runs effects twice in dev; without this the restore toast fires twice
  const restored = useRef(false);

  useEffect(() => {
    if (restored.current) return;
    restored.current = true;

    const result = load();
    if (!result) return;

    const { state, droppedNodeCount, droppedEdgeCount } = result;
    setWorkflowName(state.workflowName);
    setNodes(state.nodes);
    setEdges(state.edges);
    setSavedAt(state.savedAt);

    const label = state.workflowName || 'untitled-workflow';
    toast.info(`Restored "${label}" - last saved ${formatRelativeTime(state.savedAt)}.`);

    if (droppedNodeCount > 0 || droppedEdgeCount > 0) {
      toast.warning('Some components could not be restored - they may have been removed.');
    }
  }, [load, setNodes, setEdges]);

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
    const state: PersistedWorkflowState = {
      workflowName,
      nodes,
      edges,
      savedAt: new Date().toISOString(),
    };

    if (!save(state)) {
      toast.error('Could not save - browser storage is full.');
      return;
    }

    setSavedAt(state.savedAt);
    toast.success('Workflow saved.');
  }, [workflowName, nodes, edges, save]);

  const handleClear = useCallback(() => {
    clear();
    setWorkflowName('');
    setNodes([]);
    setEdges([]);
    setSavedAt(null);
  }, [clear, setNodes, setEdges]);

  return (
    // required for WorkflowCanvas's useReactFlow()/screenToFlowPosition call
    <ReactFlowProvider>
      <div className="flex h-full flex-col">
        <WorkflowTopBar
          workflowName={workflowName}
          onWorkflowNameChange={setWorkflowName}
          onSave={handleSave}
          savedAt={savedAt}
          onClear={handleClear}
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
