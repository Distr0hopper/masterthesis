import { toolTransformer, type ToolDetailDisplayModel, type ToolDisplayModel } from '@/api/tools/transformer';
import {
  workflowTransformer,
  type WorkflowDetailDisplayModel,
  type WorkflowDisplayModel,
} from '@/api/workflows/transformer';
import type { UpdateComponentFormData } from './schema';
import type { ComponentDetailDto, ComponentListItemDto } from './types';

// The composite's uniform view in the UI: one display model per kind, dispatched on `kind`.
// Kept apart from transformer.ts so the kind-specific transformers can build on its helpers
// without an import cycle.

/** A list row of either kind - narrow it on `kind`. */
export type ComponentDisplayModel = ToolDisplayModel | WorkflowDisplayModel;
/** A detail view of either kind - narrow it on `kind`. */
export type ComponentDetailDisplayModel = ToolDetailDisplayModel | WorkflowDetailDisplayModel;

export const componentTransformer = {
  toDisplayModel(dto: ComponentListItemDto): ComponentDisplayModel {
    return dto.kind === 'tool' ? toolTransformer.toDisplayModel(dto) : workflowTransformer.toDisplayModel(dto);
  },

  toListDisplayModels(dtos: ComponentListItemDto[]): ComponentDisplayModel[] {
    // self-reference by name, not `this` - toListDisplayModel() passes this method
    // around as a bare function reference, which would drop a `this` binding
    return dtos.map((dto) => componentTransformer.toDisplayModel(dto));
  },

  toDetailDisplayModel(dto: ComponentDetailDto): ComponentDetailDisplayModel {
    return dto.kind === 'tool'
      ? toolTransformer.toDetailDisplayModel(dto)
      : workflowTransformer.toDetailDisplayModel(dto);
  },

  getInitialUpdateFormValues(component: ComponentDisplayModel): UpdateComponentFormData {
    return { domains: component.domains, description: component.description ?? '' };
  },
};
