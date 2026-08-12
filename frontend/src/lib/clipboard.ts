import { toast } from 'sonner';

export function copyToClipboard(content: string): void {
  navigator.clipboard
    .writeText(content)
    .then(() => toast.success('Copied to clipboard'))
    .catch(() => toast.error('Could not copy to clipboard'));
}
