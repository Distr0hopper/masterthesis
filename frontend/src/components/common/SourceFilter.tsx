import { ChevronDown } from 'lucide-react';
import { Button } from '@/components/ui/button.tsx';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu.tsx';
import { SOURCE_LABELS, type ComponentSource } from '@/api/components';
import { parseSource } from '@/lib/componentSources';
import { cn } from '@/lib/utils';

const ALL = 'all';

interface SourceFilterProps {
  /** undefined means "all sources", i.e. no filter */
  value: ComponentSource | undefined;
  onValueChange: (value: ComponentSource | undefined) => void;
  /** the sources to offer - e.g. only the ones the selected kind can come from */
  sources: readonly ComponentSource[];
  className?: string;
  id?: string;
}

/** Single-choice filter by where a component came from - packaged, uploaded or built. */
export function SourceFilter({ value, onValueChange, sources, className, id }: SourceFilterProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          id={id}
          type="button"
          variant="outline"
          className={cn('h-10 w-full justify-between font-normal', className)}
        >
          {value ? SOURCE_LABELS[value] : 'All Sources'}
          <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="start" className="w-56">
        <DropdownMenuRadioGroup value={value ?? ALL} onValueChange={(next) => onValueChange(parseSource(next))}>
          <DropdownMenuRadioItem value={ALL}>All Sources</DropdownMenuRadioItem>
          <DropdownMenuSeparator />
          {sources.map((source) => (
            <DropdownMenuRadioItem key={source} value={source}>
              {SOURCE_LABELS[source]}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
