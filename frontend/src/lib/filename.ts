/** Extensions the upload flows accept - a .cwl document or a .zip archive of them. */
const UPLOAD_EXTENSION = /\.(cwl|zip)$/i;

/**
 * `remove-outliers.cwl` -> `remove-outliers`, `bundle.zip` -> `bundle`.
 *
 * Used to suggest a name from the dropped file. Mirrors the backend's
 * workflow_parser.strip_cwl_extension, which does the same for the CWL it parses.
 */
export function stripUploadExtension(filename: string): string {
  return filename.replace(UPLOAD_EXTENSION, '');
}
