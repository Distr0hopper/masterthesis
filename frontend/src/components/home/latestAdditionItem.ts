import type { ComponentDisplayModel, ComponentKind } from '@/api/components';
import { componentDetailRoute } from '@/lib/routes';

export interface LatestAdditionItem {
  id: string;
  name: string;
  subtitle: string;
  href: string;
  kind: ComponentKind;
  badgeLabel: string;
}

export function toLatestAdditionItems(components: ComponentDisplayModel[]): LatestAdditionItem[] {
  return components.map((c) => ({
    id: c.id,
    name: c.name,
    subtitle: `${c.domainsDisplay.join(', ')} · ${c.createdAtDisplay}`,
    href: componentDetailRoute(c.kind, c.id),
    kind: c.kind,
    badgeLabel: c.kindDisplay,
  }));
}
