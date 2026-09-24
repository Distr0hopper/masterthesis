import type { ConnectionStatus } from '@/api/components/types';

/** A builder edge: the output `sourcePort` of one component feeding the input `targetPort` of another. */
export interface ConnectionDto {
  sourceComponentId: string;
  sourcePort: string;
  targetComponentId: string;
  targetPort: string;
}

export type UnverifiedReason =
  | 'missing-formats'
  | 'missing-input-format'
  | 'missing-output-format'
  | 'unknown-ontology'
  | 'different-ontology'
  | 'not-checked';

/** The backend's verdict on one connection. */
export interface ConnectionCheckDto {
  status: ConnectionStatus;
  reason: UnverifiedReason | null;
  message: string | null;
}

export interface CompatibilityResponseDto {
  results: ConnectionCheckDto[];
}
