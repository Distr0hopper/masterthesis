import { Badge } from '@/components/ui/badge.tsx';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table.tsx';
import type { ParameterDisplayModel } from '@/api/components';
import { ParameterDirection } from '@/api/components/types';

const DIRECTION_BADGE_CLASSNAME: Record<ParameterDirection, string> = {
  [ParameterDirection.INPUT]: 'border-blue-300 text-blue-700',
  [ParameterDirection.OUTPUT]: 'border-green-300 text-green-700',
};

interface ParameterTableProps {
  parameters: ParameterDisplayModel[];
}

export function ParameterTable({ parameters }: ParameterTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Type</TableHead>
          <TableHead>Direction</TableHead>
          <TableHead>Default</TableHead>
          <TableHead>Format</TableHead>
          <TableHead>Description</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {parameters.map((parameter) => (
          <TableRow key={parameter.id}>
            <TableCell className="font-mono font-semibold">{parameter.name}</TableCell>
            <TableCell className="font-mono text-slate-500">{parameter.cwlType}</TableCell>
            <TableCell>
              <Badge variant="outline" className={DIRECTION_BADGE_CLASSNAME[parameter.direction]}>
                {parameter.directionDisplay}
              </Badge>
            </TableCell>
            <TableCell className="text-slate-500">{parameter.defaultValue ?? '—'}</TableCell>
            <TableCell className="text-slate-500">
              {parameter.format ? (
                parameter.format.startsWith('http') ? (
                  <a
                    href={parameter.format}
                    target="_blank"
                    rel="noreferrer"
                    className="text-jmu-blue-800 hover:underline"
                  >
                    {parameter.formatLabel ?? parameter.format}
                  </a>
                ) : (
                  (parameter.formatLabel ?? parameter.format)
                )
              ) : (
                '—'
              )}
            </TableCell>
            <TableCell className="text-slate-500">{parameter.description ?? '—'}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
