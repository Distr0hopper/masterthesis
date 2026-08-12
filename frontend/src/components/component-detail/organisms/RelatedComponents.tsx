import { Card, CardContent } from '@/components/ui/card.tsx';

export function RelatedComponents() {
  return (
    <Card className="mt-6">
      <CardContent className="pt-6">
        <h3 className="font-semibold text-slate-900">Related Components</h3>
        <p className="mt-1 text-sm italic text-slate-500">
          Components in the same domain will appear here. — Coming in a future release.
        </p>
      </CardContent>
    </Card>
  );
}
