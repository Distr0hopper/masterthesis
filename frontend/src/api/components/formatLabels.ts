import { FormatLabelSource, type FormatLabelDto, type ParameterDirection } from './types';

/**
 * The parameter fields the hand-label helpers read - fits DTOs and display models alike.
 * Which ports accept a label, and where a label came from, are the backend's decisions
 * (`acceptsManualFormatLabel`, `formatLabelSource`); these helpers only read them.
 */
interface LabelablePort {
  name: string;
  direction: ParameterDirection;
  formatLabel: string | null;
  formatLabelSource?: FormatLabelSource | null;
  acceptsManualFormatLabel?: boolean;
}

/** Hand-written labels being edited, keyed by {@link formatLabelKey}. */
export type FormatLabelDraft = Record<string, string>;

export const formatLabelKey = (port: Pick<LabelablePort, 'name' | 'direction'>) => `${port.direction}:${port.name}`;

/**
 * Whether a port's label was written by hand. Canvases saved before the backend sent
 * `formatLabelSource` carry parameters without it - those show no hint.
 */
export function isManualFormatLabel(port: LabelablePort): boolean {
  return port.formatLabelSource === FormatLabelSource.MANUAL;
}

/**
 * Whether a port has an ontology format whose name couldn't be looked up - the format
 * service was unreachable on upload, or the ontology has no label for it (e.g. EDAM's
 * format_4125 "raster"). The format is still real and still checked; only its name is missing.
 */
export function isUnresolvedFormatLabel(port: LabelablePort): boolean {
  return port.formatLabelSource === FormatLabelSource.UNRESOLVED;
}

export const UNRESOLVED_FORMAT_HINT =
  'Format from the ontology, but its name could not be looked up. Connections to this port are still checked.';

export function labelablePorts<T extends LabelablePort>(parameters: T[]): T[] {
  return parameters.filter((p) => p.acceptsManualFormatLabel);
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
  return parameters.map((p) => {
    if (!p.acceptsManualFormatLabel || !(formatLabelKey(p) in draft)) return p;
    const label = draft[formatLabelKey(p)].trim() || null;
    return { ...p, formatLabel: label, formatLabelSource: label ? FormatLabelSource.MANUAL : null };
  });
}
