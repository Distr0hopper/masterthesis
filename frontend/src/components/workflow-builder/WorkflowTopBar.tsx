import { Button } from '@/components/ui/button.tsx';
import { Input } from '@/components/ui/input.tsx';

interface WorkflowTopBarProps {
  name: string;
  onNameChange: (value: string) => void;
}

export function WorkflowTopBar({ name, onNameChange }: WorkflowTopBarProps) {
  return (
    <div className="flex h-14 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-4">
      <Input
        placeholder="untitled-workflow"
        value={name}
        onChange={(e) => onNameChange(e.target.value)}
        className="max-w-xs border-0 font-mono shadow-none focus-visible:ring-0 focus-visible:ring-offset-0"
      />

      <div className="flex items-center gap-2">
        {/* wired up in AP 3 (persistence) */}
        <Button variant="outline" disabled>
          Save
        </Button>
        {/* wired up in AP 4 (CWL generation) */}
        <Button disabled className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90">
          Export CWL
        </Button>
      </div>
    </div>
  );
}
