import type { Edge } from '@xyflow/react';
import { DEFAULT_WORKFLOW_NAME } from './canvasState';
import { dataInputs } from './portKinds';
import type { ComponentFlowNode } from '../types';

export type ValidationErrorType =
  | 'no_nodes'
  | 'no_workflow_name'
  | 'disconnected_node'
  | 'unresolved_component'
  | 'missing_component'
  | 'unconnected_input';

export interface ValidationError {
  type: ValidationErrorType;
  message: string;
  nodeId?: string;
}

/**
 * Checks the canvas can produce a meaningful CWL Workflow. Pure - no React, no network -
 * so it is unit-testable and can run before any request is made.
 *
 * The backend re-checks everything that would make an export structurally invalid
 * (empty canvas, missing components, cycles); this exists to fail fast with a message
 * that names the offending component.
 */
export function validateCanvas(
  nodes: ComponentFlowNode[],
  edges: Edge[],
  workflowName: string,
  /** componentIds the backend reported as deleted - see WorkflowDraftDetailDto */
  missingComponentIds: ReadonlySet<string> = new Set(),
): ValidationError[] {
  const errors: ValidationError[] = [];

  if (nodes.length === 0) {
    // nothing else is worth reporting against an empty canvas
    return [{ type: 'no_nodes', message: 'The canvas is empty. Add at least one component.' }];
  }

  const trimmed = workflowName.trim();
  if (!trimmed || trimmed === DEFAULT_WORKFLOW_NAME) {
    errors.push({
      type: 'no_workflow_name',
      message: 'Give your workflow a name before exporting.',
    });
  }

  const connectedNodeIds = new Set(edges.flatMap((e) => [e.source, e.target]));

  for (const node of nodes) {
    // a single-node workflow is legitimately edge-free, so only flag islands in a graph
    if (nodes.length > 1 && !connectedNodeIds.has(node.id)) {
      errors.push({
        type: 'disconnected_node',
        message: `"${node.data.label}" is not connected to any other component.`,
        nodeId: node.id,
      });
    }

    if (!node.data.componentId) {
      errors.push({
        type: 'unresolved_component',
        message: `"${node.data.label}" has no linked component in the repository.`,
        nodeId: node.id,
      });
    } else if (missingComponentIds.has(node.data.componentId)) {
      errors.push({
        type: 'missing_component',
        message: `"${node.data.label}" was deleted from the repository. Remove it from the canvas or replace it with another component.`,
        nodeId: node.id,
      });
    }
  }

  // A File input nothing feeds becomes a workflow-level input, which is valid CWL but
  // usually means the user forgot a wire. Reported so it is a deliberate choice.
  const filledInputs = new Set(edges.map((e) => `${e.target}:${e.targetHandle}`));
  for (const node of nodes) {
    for (const port of dataInputs(node.data.parameters)) {
      if (!filledInputs.has(`${node.id}:${port.name}`)) {
        errors.push({
          type: 'unconnected_input',
          message: `"${node.data.label}" input "${port.name}" is not connected - it will become an input of the whole workflow.`,
          nodeId: node.id,
        });
      }
    }
  }

  return errors;
}

/** Blocking problems only. `unconnected_input` is advisory - valid CWL, just worth knowing. */
export function isBlocking(error: ValidationError): boolean {
  return error.type !== 'unconnected_input';
}
