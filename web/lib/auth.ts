/**
 * Validates HTTP Basic Authentication credentials.
 * Secures SSR routes and Server Actions against unauthorized access.
 * Uses Web Crypto SHA-256 constant-time comparison and proper UTF-8 decoding.
 */

/**
 * Decodes base64 string to UTF-8 properly in both Node.js and Edge runtimes,
 * avoiding corrupting accented characters or emojis.
 */
export function decodeBase64Utf8(base64: string): string {
  if (typeof Buffer !== 'undefined') {
    return Buffer.from(base64, 'base64').toString('utf-8');
  }
  const binaryString = atob(base64);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return new TextDecoder().decode(bytes);
}

/**
 * Compares two strings in constant time by comparing their SHA-256 digests.
 * Completely eliminates timing side-channel attacks and prevents length leakage.
 */
export async function safeCompare(a: string, b: string): Promise<boolean> {
  const encoder = new TextEncoder();
  const hashABuffer = await crypto.subtle.digest('SHA-256', encoder.encode(a));
  const hashBBuffer = await crypto.subtle.digest('SHA-256', encoder.encode(b));

  const viewA = new Uint8Array(hashABuffer);
  const viewB = new Uint8Array(hashBBuffer);

  let diff = 0;
  for (let i = 0; i < viewA.length; i++) {
    diff |= viewA[i] ^ viewB[i];
  }
  return diff === 0;
}

export interface AuthValidationResult {
  authorized: boolean;
  reason?: 'missing_env' | 'missing_header' | 'malformed_header' | 'invalid_credentials';
}

/**
 * Validates HTTP Basic Authentication header against configured credentials.
 * Fails closed if expected credentials are not configured.
 */
export async function validateBasicAuth(
  authHeader: string | null,
  expectedUser: string | undefined,
  expectedPass: string | undefined
): Promise<AuthValidationResult> {
  // Fail-closed: missing credentials always rejects
  if (!expectedUser || !expectedPass) {
    return { authorized: false, reason: 'missing_env' };
  }

  if (!authHeader || !authHeader.startsWith('Basic ')) {
    return { authorized: false, reason: 'missing_header' };
  }

  const base64 = authHeader.slice(6).trim();
  if (!base64) {
    return { authorized: false, reason: 'malformed_header' };
  }

  try {
    const decoded = decodeBase64Utf8(base64);
    const separatorIndex = decoded.indexOf(':');
    if (separatorIndex === -1) {
      return { authorized: false, reason: 'malformed_header' };
    }

    const user = decoded.substring(0, separatorIndex);
    const pass = decoded.substring(separatorIndex + 1);

    const userMatches = await safeCompare(user, expectedUser);
    const passMatches = await safeCompare(pass, expectedPass);

    if (userMatches && passMatches) {
      return { authorized: true };
    }

    return { authorized: false, reason: 'invalid_credentials' };
  } catch {
    return { authorized: false, reason: 'malformed_header' };
  }
}
