import * as React from 'react';
import { getDomainLabel, type DomainDto } from '@/api/components';
import { cn } from '@/lib/utils';

interface DomainSelectProps
  extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, 'value' | 'onChange'> {
  value: string;
  domains: DomainDto[];
  onValueChange: (value: string) => void;
}

/**
 * The project has no Radix select primitive installed, so every domain filter is a native
 * <select> with the same styling. This is that markup in one place - the component
 * browser, the workflow browser and the workflow builder palette all render it.
 */
export function DomainSelect({
  value,
  domains,
  onValueChange,
  className,
  ...props
}: DomainSelectProps) {
  return (
    <select
      value={value}
      onChange={(e) => onValueChange(e.target.value)}
      className={cn(
        'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-base ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 md:text-sm',
        className,
      )}
      {...props}
    >
      <option value="">All Domains</option>
      {domains.map((domain) => (
        <option key={domain.id} value={domain.id}>
          {getDomainLabel(domain.id)}
        </option>
      ))}
    </select>
  );
}
