// In-memory sliding window rate limiter
const rateLimitMap = new Map<string, { count: number; resetAt: number }>();
const RATE_LIMIT_WINDOW_MS = 60 * 1000;
const MAX_REQUESTS_PER_WINDOW = 30;
export const MAX_MAP_ENTRIES = 5000;
const PRUNE_INTERVAL_MS = 15 * 1000;
let lastPruneTime = 0;

/**
 * Throttled cleanup of expired entries (at most once every 15s) to avoid Event Loop stalls.
 */
function pruneExpiredEntries(now: number): void {
  if (now - lastPruneTime < PRUNE_INTERVAL_MS) return;
  lastPruneTime = now;

  rateLimitMap.forEach((record, key) => {
    if (now > record.resetAt) {
      rateLimitMap.delete(key);
    }
  });
}

/**
 * Hard ceiling enforcement with FIFO eviction.
 * Prevents memory leak and unbounded Map growth under high-entropy IP attacks.
 */
function enforceCapacity(): void {
  while (rateLimitMap.size >= MAX_MAP_ENTRIES) {
    const oldestKey = rateLimitMap.keys().next().value;
    if (oldestKey === undefined) break;
    rateLimitMap.delete(oldestKey);
  }
}

/**
 * Resolves real client IP safely, prioritizing trusted edge/reverse proxy headers.
 */
export function getClientIp(reqHeaders: { get: (name: string) => string | null }): string {
  // 1. Cloudflare Connecting IP (injected by Cloudflare edge)
  const cfIp = reqHeaders.get('cf-connecting-ip');
  if (cfIp) return cfIp.trim();

  // 2. Vercel Real IP (injected by Vercel edge)
  const vercelIp = reqHeaders.get('x-vercel-ip');
  if (vercelIp) return vercelIp.trim();

  // 3. Real-IP set by trusted reverse proxy (e.g. Nginx, Traefik)
  const realIp = reqHeaders.get('x-real-ip');
  if (realIp) return realIp.trim();

  // 4. X-Forwarded-For: client origin is first hop
  const forwardedFor = reqHeaders.get('x-forwarded-for');
  if (forwardedFor) {
    const parts = forwardedFor
      .split(',')
      .map((p) => p.trim())
      .filter(Boolean);
    if (parts.length > 0) {
      return parts[0];
    }
  }

  return 'local-client';
}

/**
 * Checks and updates rate limit counter for a given client identifier (e.g. IP).
 * Returns true if the request is within allowable limits, false if throttled.
 */
export function checkRateLimit(
  clientId: string,
  windowMs = RATE_LIMIT_WINDOW_MS,
  maxLimit = MAX_REQUESTS_PER_WINDOW
): boolean {
  const now = Date.now();
  pruneExpiredEntries(now);

  const record = rateLimitMap.get(clientId);

  if (!record || now > record.resetAt) {
    enforceCapacity();
    rateLimitMap.set(clientId, { count: 1, resetAt: now + windowMs });
    return true;
  }

  if (record.count >= maxLimit) {
    return false;
  }

  record.count += 1;
  return true;
}

/**
 * Returns current size of rate limit map (for testing).
 */
export function getRateLimitMapSize(): number {
  return rateLimitMap.size;
}

/**
 * Clears in-memory rate limit store (for testing).
 */
export function resetRateLimits(): void {
  rateLimitMap.clear();
  lastPruneTime = 0;
}
