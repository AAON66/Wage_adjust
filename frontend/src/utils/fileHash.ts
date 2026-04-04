/**
 * Compute SHA-256 hash of a File using the Web Crypto API.
 * Returns lowercase hex string (64 chars).
 */
export async function computeFileSHA256(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
}
