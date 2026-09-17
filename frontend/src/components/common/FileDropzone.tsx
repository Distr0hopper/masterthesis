import { useRef, useState } from 'react';
import { Upload, X } from 'lucide-react';
import { Label } from '@/components/ui/label.tsx';
import { cn } from '@/lib/utils';

interface FileDropzoneProps {
  value: File | null;
  onChange: (file: File | null) => void;
  accept: string;
  label: string;
  /** shown under the drag prompt in the empty state - defaults to "or click to browse" */
  helperText?: string;
  error?: string;
}

/**
 * Generic drag-and-drop file picker, shared by every file-upload form in the app
 * (component upload, workflow upload, the workflow parse preview) - parameterised by
 * accept/label/helperText instead of hardcoding one file type per form.
 */
export function FileDropzone({ value, onChange, accept, label, helperText, error }: FileDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFiles = (files: FileList | null) => {
    const file = files?.[0];
    if (file) onChange(file);
  };

  return (
    <div className="flex flex-col gap-2">
      <Label>{label}</Label>

      {value ? (
        <div className="flex items-center justify-between rounded-md border border-input bg-background px-4 py-3">
          <span className="font-mono text-sm text-slate-900">{value.name}</span>
          <button
            type="button"
            onClick={() => onChange(null)}
            className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900"
          >
            <X className="h-4 w-4" /> Change file
          </button>
        </div>
      ) : (
        <div
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragging(false);
            handleFiles(e.dataTransfer.files);
          }}
          className={cn(
            'flex cursor-pointer flex-col items-center justify-center gap-2 rounded-md border-2 border-dashed px-6 py-12 text-center transition-colors',
            isDragging ? 'border-jmu-blue-800 bg-jmu-blue-50' : 'border-input hover:border-slate-300',
          )}
        >
          <Upload className="h-8 w-8 text-slate-400" />
          <p className="font-medium text-slate-900">Drag and drop a file here</p>
          <p className="text-sm text-slate-500">{helperText ?? 'or click to browse'}</p>
        </div>
      )}

      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />

      {error && <p className="text-sm text-error-foreground">{error}</p>}
    </div>
  );
}
