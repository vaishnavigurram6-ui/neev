// Matches the backend's supported envelope types and per-file size cap.
export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;
export const ACCEPT = 'application/pdf,image/jpeg,image/png,image/webp';

export function looksReadable(file: Pick<File, 'type' | 'name'>): boolean {
  if (file.type) return ACCEPT.split(',').includes(file.type);
  return /\.(pdf|jpe?g|png|webp)$/i.test(file.name);
}