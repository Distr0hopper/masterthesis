export function downloadFile(url: string): void {
  window.location.href = url;
}

export function downloadBlob(filename: string, blob: Blob): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function downloadTextFile(filename: string, content: string): void {
  downloadBlob(filename, new Blob([content], { type: 'text/plain' }));
}
