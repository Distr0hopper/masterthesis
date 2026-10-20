import { ComponentStatus } from '@/api/components/types';

/** Every status in the order an owner's lists show them - a draft needs attention first. */
export const STATUS_ORDER = [ComponentStatus.DRAFT, ComponentStatus.PUBLISHED, ComponentStatus.DEPRECATED] as const;

/**
 * What a group of one status is called on an owner's own pages (sections, filters). Not
 * `STATUS_LABELS`: a draft reads "Unpublished" there, as seen from the owner's side.
 */
export const STATUS_GROUP_TITLES: Record<ComponentStatus, string> = {
  [ComponentStatus.DRAFT]: 'Unpublished',
  [ComponentStatus.PUBLISHED]: 'Published',
  [ComponentStatus.DEPRECATED]: 'Deprecated',
};

/** `value` as a status, or undefined when it is none - for statuses read from the URL. */
export function parseStatus(value: string | null): ComponentStatus | undefined {
  return STATUS_ORDER.find((status) => status === value);
}
