import { Card, CardContent } from '@/components/ui/card.tsx';
import { Badge } from '@/components/ui/badge.tsx';

// no backend tagging concept exists - purely decorative, matching the mockup
const TAGS = ['CWL', 'CommandLineTool', 'Workflow', 'Docker', 'MoveApps', 'Movement Ecology', 'Earth Observation'];

export function HomeTags() {
  return (
    <Card>
      <CardContent className="pt-6">
        <h3 className="font-semibold text-slate-900">Tags</h3>
        <div className="mt-3 flex flex-wrap gap-2">
          {TAGS.map((tag) => (
            <Badge key={tag} variant="secondary">
              {tag}
            </Badge>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
