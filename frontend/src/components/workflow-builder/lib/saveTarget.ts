import { ComponentStatus, STATUS_LABELS } from '@/api/components';
import type { LinkedWorkflowDto } from '@/api/workflow-drafts';

/**
 * What the Save button says it will do in My Components - before the click, not after:
 * once the newest version is public, a Save no longer changes it but starts the next one.
 */
export function saveTarget(linked: LinkedWorkflowDto | null): { label: string; hint: string } {
  if (!linked) {
    return { label: 'Save', hint: 'Saves the canvas and adds it to My Components as a draft only you can see' };
  }
  if (linked.status === ComponentStatus.DRAFT) {
    return { label: 'Save', hint: `Saves the canvas and updates the draft v${linked.version} in My Components` };
  }
  const next = linked.version + 1;
  return {
    label: `Save as v${next}`,
    hint: `v${linked.version} stays ${STATUS_LABELS[linked.status].toLowerCase()} - v${next} is a draft only you can see until you publish it`,
  };
}
