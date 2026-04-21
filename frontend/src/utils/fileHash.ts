/**
 * Compute SHA-256 hash of a File using the Web Crypto API.
 * Returns lowercase hex string (64 chars).
 *
 * 在非安全上下文（HTTP）下 `crypto.subtle` 不可用 —— 抛出带标记的错误，
 * 调用方据此跳过查重并正常上传，不打扰用户。
 */
export function isSubtleCryptoAvailable(): boolean {
  return typeof crypto !== 'undefined'
    && typeof crypto.subtle !== 'undefined'
    && typeof crypto.subtle.digest === 'function';
}

export class SubtleCryptoUnavailableError extends Error {
  constructor() {
    super('crypto.subtle is unavailable in this context (likely non-HTTPS)');
    this.name = 'SubtleCryptoUnavailableError';
  }
}

export async function computeFileSHA256(file: File): Promise<string> {
  if (!isSubtleCryptoAvailable()) {
    throw new SubtleCryptoUnavailableError();
  }
  const buffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
}
