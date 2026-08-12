import { Copy, Download } from 'lucide-react';
import { Button } from '@/components/ui/button.tsx';
import { copyToClipboard } from '@/lib/clipboard';
import { downloadFile, downloadTextFile } from '@/lib/download';

interface CodeBlockProps {
  title: string;
  content: string;
  // exactly one is expected to be set by the caller: downloadUrl for content backed by a
  // real backend file endpoint, downloadFilename to save the already-fetched `content` as
  // a client-side blob when no such endpoint exists
  downloadUrl?: string;
  downloadFilename?: string;
}

export function CodeBlock({ title, content, downloadUrl, downloadFilename }: CodeBlockProps) {
  const handleDownload = () => {
    if (downloadUrl) {
      downloadFile(downloadUrl);
    } else if (downloadFilename) {
      downloadTextFile(downloadFilename, content);
    }
  };

  return (
    <div className="overflow-hidden rounded-lg border">
      <div className="flex items-center justify-between border-b bg-slate-50 px-4 py-2">
        <span className="font-mono text-sm text-slate-500">{title}</span>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={() => copyToClipboard(content)}>
            <Copy className="mr-1 h-4 w-4" /> Copy
          </Button>
          <Button variant="ghost" size="sm" onClick={handleDownload}>
            <Download className="mr-1 h-4 w-4" /> Download
          </Button>
        </div>
      </div>
      <pre className="max-h-[600px] overflow-auto bg-slate-900 p-4 text-sm text-slate-100">
        <code>{content}</code>
      </pre>
    </div>
  );
}
