import { FormatLabelSource, UNRESOLVED_FORMAT_HINT, type ParameterDisplayModel } from '@/api/components';

/**
 * TODO: Add consistent format.
 * Human-readable format for a port. `format` is inconsistent across components: often
 * null, sometimes a bare token ("rds"), sometimes an ontology URI. `formatLabel` is the
 * resolved name when one exists; otherwise a URI is reduced to its last segment so it
 * stays readable on a node card.
 */
export function formatLabelFor(parameter: ParameterDisplayModel): string | null {
  if (parameter.formatLabel) return parameter.formatLabel;
  if (!parameter.format) return null;
  if (!parameter.format.startsWith('http')) return parameter.format;
  const lastSegment = parameter.format.split(/[/#]/).filter(Boolean).pop();
  return lastSegment ?? parameter.format;
}

/** "File" or "File · rds" - the type line under a port name. */
export function formatPortType(parameter: ParameterDisplayModel): string {
  const format = formatLabelFor(parameter);
  return format ? `${parameter.cwlType} · ${format}` : parameter.cwlType;
}

/**
 * What the inspector says about a File port's format when it needs explaining: a hand-written
 * label, an ontology format without a name, or a format that can't be verified. Null for an
 * ontology format with its label.
 */
export function formatNoteFor(parameter: ParameterDisplayModel): string | null {
  switch (parameter.formatLabelSource) {
    case FormatLabelSource.MANUAL:
      return `"${parameter.formatLabel}" was entered by hand by the component's author. It is not from an ontology, so connections to this port cannot be verified.`;
    case FormatLabelSource.UNRESOLVED:
      return UNRESOLVED_FORMAT_HINT;
    case FormatLabelSource.ONTOLOGY:
      return null;
  }
  // canvases saved before the backend sent formatLabelSource: nothing to say reliably
  if (parameter.formatLabelSource === undefined) return null;
  if (!parameter.format) return 'No format declared - connections to this port cannot be verified.';
  return `"${parameter.format}" is not an ontology format, so connections to this port cannot be verified.`;
}
