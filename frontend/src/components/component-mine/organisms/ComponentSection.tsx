import { ComponentCard } from '@/components/component-browse/ComponentCard';
import { MineSection } from '@/components/common/MineSection';
import { MyComponentCardActions } from './MyComponentCardActions';
import type { ComponentDisplayModel } from '@/api/components';

interface ComponentSectionProps {
  title: string;
  components: ComponentDisplayModel[];
  total: number;
  /** where a card's detail page leads back to */
  backTo: string;
}

export function ComponentSection({ title, components, total, backTo }: ComponentSectionProps) {
  return (
    <MineSection title={title} total={total}>
      {components.map((component) => (
        <ComponentCard
          key={component.id}
          component={component}
          backTo={backTo}
          showBuilderLink
          actions={<MyComponentCardActions component={component} />}
        />
      ))}
    </MineSection>
  );
}
