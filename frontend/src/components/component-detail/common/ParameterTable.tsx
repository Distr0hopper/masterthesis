import { Badge } from '@/components/ui/badge.tsx';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table.tsx';
import { isManualFormatLabel, type ParameterDisplayModel } from '@/api/components';
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
              <FormatCell parameter={parameter} />
            </TableCell>
            <TableCell className="text-slate-500">{parameter.description ?? '—'}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

/**
 * The resolved label when there is one, else the raw format. A label can exist without a
 * format - one written by hand (e.g. "RDS") for a port no ontology covers - and is marked
 * as such, so it isn't mistaken for a verified ontology format.
 */
function FormatCell({ parameter }: { parameter: ParameterDisplayModel }) {
  const text = parameter.formatLabel ?? parameter.format;
  if (!text) return <>—</>;

  const isManual = isManualFormatLabel(parameter);
  return (
    <>
      {parameter.format?.startsWith('http') ? (
        <a href={parameter.format} target="_blank" rel="noreferrer" className="text-jmu-blue-800 hover:underline">
          {text}
        </a>
      ) : (
        text
      )}
      {isManual && (
        <span className="ml-1 text-xs text-slate-400" title="Entered by hand - not from an ontology, not verified">
          (manual)
        </span>
      )}
    </>
  );
}
