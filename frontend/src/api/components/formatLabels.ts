import { ParameterDirection, type FormatLabelDto } from './types';

/** The parameter fields the hand-label rules read - fits DTOs and display models alike. */
interface LabelablePort {
  name: string;
  cwlType: string;
  direction: ParameterDirection;
  format: string | null;
  formatLabel: string | null;
  ontologyUrl: string | null;
}

/** Hand-written labels being edited, keyed by {@link formatLabelKey}. */
export type FormatLabelDraft = Record<string, string>;

export const formatLabelKey = (port: Pick<LabelablePort, 'name' | 'direction'>) => `${port.direction}:${port.name}`;

/**
 * Whether a port's label is the user's to write - mirrors
 * ComponentsService.accepts_manual_format_label: a File port whose format no ontology
 * resolves (none at all, or a bare token like `rds` - only a namespaced format is a URI).
 */
export function acceptsManualFormatLabel(port: LabelablePort): boolean {
  const isFile = port.cwlType.trim().toLowerCase().startsWith('file');
  const hasOntologyFormat = Boolean(port.format?.includes('://') && port.ontologyUrl);
  return isFile && !hasOntologyFormat;
}

/**
 * Whether a port's label was written by hand rather than resolved from an ontology.
 * `ontologyUrl` is checked for undefined on purpose: canvases saved before it existed
 * carry parameters without it, and every label from that time was ontology-resolved.
 */
export function isManualFormatLabel(port: LabelablePort): boolean {
  return Boolean(port.formatLabel) && port.ontologyUrl !== undefined && acceptsManualFormatLabel(port);
}

export function labelablePorts<T extends LabelablePort>(parameters: T[]): T[] {
  return parameters.filter(acceptsManualFormatLabel);
}

/** The labels a component already carries, as an editable draft. */
export function initialFormatLabelDraft(parameters: LabelablePort[]): FormatLabelDraft {
  return Object.fromEntries(labelablePorts(parameters).map((p) => [formatLabelKey(p), p.formatLabel ?? '']));
}

/** Every labelable port's entry - blank ones as null, which clears a label. */
export function toFormatLabelDtos(parameters: LabelablePort[], draft: FormatLabelDraft): FormatLabelDto[] {
  return labelablePorts(parameters).map((p) => ({
    name: p.name,
    direction: p.direction,
    label: draft[formatLabelKey(p)]?.trim() || null,
  }));
}

/** `parameters` with the draft's labels applied - so a preview shows them before saving. */
export function withFormatLabels<T extends LabelablePort>(parameters: T[], draft: FormatLabelDraft): T[] {
  return parameters.map((p) =>
    acceptsManualFormatLabel(p) && formatLabelKey(p) in draft
      ? { ...p, formatLabel: draft[formatLabelKey(p)].trim() || null }
      : p,
  );
}
