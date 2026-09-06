import { useCallback, useMemo, useState } from 'react';
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
import type { ComponentFlowNode } from '@/components/workflow-builder/types';

export default function WorkflowBuilderPage() {
  const [workflowName, setWorkflowName] = useState('');
  const [nodes, setNodes, onNodesChange] = useNodesState<ComponentFlowNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

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

      setEdges((prev) => addEdge(connection, prev));
    },
    [nodes, setEdges],
  );

  const onAddNode = useCallback(
    (node: ComponentFlowNode) => setNodes((prev) => [...prev, node]),
    [setNodes],
  );

  return (
    <ReactFlowProvider>
      <div className="flex h-full flex-col">
        <WorkflowTopBar name={workflowName} onNameChange={setWorkflowName} />
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
