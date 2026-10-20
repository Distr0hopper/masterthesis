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
import type { ComponentStatus } from '@/api/components';
import { parseStatus, STATUS_GROUP_TITLES, STATUS_ORDER } from '@/lib/componentStatuses';
import { cn } from '@/lib/utils';

const ALL = 'all';

interface StatusFilterProps {
  /** undefined means "all statuses", i.e. no filter */
  value: ComponentStatus | undefined;
  onValueChange: (value: ComponentStatus | undefined) => void;
  className?: string;
  id?: string;
}

/** Single-choice status filter for an owner's own lists - one status, or all of them. */
export function StatusFilter({ value, onValueChange, className, id }: StatusFilterProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          id={id}
          type="button"
          variant="outline"
          className={cn('h-10 w-full justify-between font-normal', className)}
        >
          {value ? STATUS_GROUP_TITLES[value] : 'All Statuses'}
          <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="start" className="w-56">
        <DropdownMenuRadioGroup value={value ?? ALL} onValueChange={(next) => onValueChange(parseStatus(next))}>
          <DropdownMenuRadioItem value={ALL}>All Statuses</DropdownMenuRadioItem>
          <DropdownMenuSeparator />
          {STATUS_ORDER.map((status) => (
            <DropdownMenuRadioItem key={status} value={status}>
              {STATUS_GROUP_TITLES[status]}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
