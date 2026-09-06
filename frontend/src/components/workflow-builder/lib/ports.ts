import type { ParameterDisplayModel } from '@/api/components';

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
