import { Code, FileCode, Package } from 'lucide-react';
import { Badge } from '@/components/ui/badge.tsx';
import { ComponentOrigin, type ParseWorkflowResponseDto } from '@/api/workflows';

interface ParsedWorkflowOverviewProps {
  parsed: ParseWorkflowResponseDto;
}

/** What the parse found, shown above the configuration cards as context for them. */
export function ParsedWorkflowOverview({ parsed }: ParsedWorkflowOverviewProps) {
  const inlineCount = parsed.componentPreviews.filter((p) => p.origin === ComponentOrigin.INLINE).length;
  const archiveCount = parsed.componentPreviews.filter((p) => p.origin === ComponentOrigin.ARCHIVE).length;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="secondary">{parsed.stepCount} step(s)</Badge>
        {parsed.isZip && <Badge variant="secondary">Archive</Badge>}
        {parsed.isSelfContained && <Badge variant="secondary">Self-contained</Badge>}
        {inlineCount > 0 && <Badge variant="secondary">{inlineCount} inline tool(s)</Badge>}
        {archiveCount > 0 && <Badge variant="secondary">{archiveCount} step file(s)</Badge>}
        {parsed.inlineOnlySteps.length > 0 && (
          <Badge variant="secondary">{parsed.inlineOnlySteps.length} inline step(s)</Badge>
        )}
      </div>

      <ul className="divide-y rounded-md border border-input">
        {parsed.componentPreviews.map((preview) => (
          <li key={preview.stepId} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2 text-sm">
            {preview.origin === ComponentOrigin.INLINE ? (
              <FileCode className="h-4 w-4 shrink-0 text-slate-400" />
            ) : (
              <Package className="h-4 w-4 shrink-0 text-slate-400" />
            )}
            <span className="font-mono text-slate-900">{preview.stepId}</span>
            <span className="text-slate-500">
              {preview.origin === ComponentOrigin.INLINE ? 'inline tool' : `from ${preview.runReference}`}
            </span>
            {preview.suggestedMatch ? (
              <Badge variant="secondary">
                matches {preview.suggestedMatch.name} v{preview.suggestedMatch.version}
              </Badge>
            ) : (
              <Badge variant="secondary">new component</Badge>
            )}
          </li>
        ))}
        {parsed.inlineOnlySteps.map((stepId) => (
          <li key={stepId} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2 text-sm">
            <Code className="h-4 w-4 shrink-0 text-slate-400" />
            <span className="font-mono text-slate-900">{stepId}</span>
            <span className="text-slate-500">inline definition (not a tool)</span>
            <Badge variant="secondary">stays in the workflow</Badge>
          </li>
        ))}
        {parsed.componentPreviews.length === 0 && parsed.inlineOnlySteps.length === 0 && (
          <li className="px-3 py-2 text-sm text-slate-500">No components could be read from this file.</li>
        )}
      </ul>
    </div>
  );
}
