import { Check, ChevronDown } from 'lucide-react';
import { Button } from '@/components/ui/button.tsx';
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu.tsx';
import { getDomainLabel, type DomainDto } from '@/api/components';
import { cn } from '@/lib/utils';

interface DomainFilterProps {
  /** selected domain ids - empty means "all domains", i.e. no filter */
  value: string[];
  domains: DomainDto[];
  onValueChange: (value: string[]) => void;
  className?: string;
  id?: string;
  'aria-label'?: string;
}

function summarise(value: string[]): string {
  if (value.length === 0) return 'All Domains';
  if (value.length === 1) return getDomainLabel(value[0]);
  return `${value.length} domains`;
}

/**
 * Multi-select domain filter, shared by the component browser, the workflow browser and
 * the workflow builder palette.
 *
 * Selecting several domains is a union: an item matching ANY of them is shown. Since a
 * component or workflow can span several domains, a single-choice dropdown could never
 * express "show me these two areas" - and the old native <select> had no room for it.
 */
export function DomainFilter({
  value,
  domains,
  onValueChange,
  className,
  id,
  'aria-label': ariaLabel,
}: DomainFilterProps) {
  const toggle = (domainId: string) => {
    onValueChange(
      value.includes(domainId) ? value.filter((d) => d !== domainId) : [...value, domainId],
    );
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          id={id}
          type="button"
          variant="outline"
          aria-label={ariaLabel}
          className={cn('h-10 w-full justify-between font-normal', className)}
        >
          {summarise(value)}
          <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="start" className="w-56">
        <DropdownMenuItem onSelect={() => onValueChange([])}>
          <Check className={cn('mr-2 h-4 w-4', value.length > 0 && 'opacity-0')} />
          All Domains
        </DropdownMenuItem>

        <DropdownMenuSeparator />

        {domains.map((domain) => (
          <DropdownMenuCheckboxItem
            key={domain.id}
            checked={value.includes(domain.id)}
            // without this the menu closes on every pick, which makes selecting a
            // second domain needlessly fiddly
            onSelect={(event) => event.preventDefault()}
            onCheckedChange={() => toggle(domain.id)}
          >
            {getDomainLabel(domain.id)}
          </DropdownMenuCheckboxItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
