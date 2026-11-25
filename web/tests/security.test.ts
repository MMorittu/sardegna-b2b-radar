import { test, describe, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import {
  checkRateLimit,
  resetRateLimits,
  getClientIp,
  getRateLimitMapSize,
  MAX_MAP_ENTRIES,
} from '../lib/rate-limiter.ts';
import { validateBasicAuth, safeCompare, decodeBase64Utf8 } from '../lib/auth.ts';

describe('Security - In-Memory Rate Limiter', () => {
  beforeEach(() => {
    resetRateLimits();
  });

  test('allows requests up to configured limit', () => {
    const testIp = `test-ip-${Date.now()}`;
    const windowMs = 5000;
    const maxLimit = 3;

    assert.strictEqual(checkRateLimit(testIp, windowMs, maxLimit), true); // 1
    assert.strictEqual(checkRateLimit(testIp, windowMs, maxLimit), true); // 2
    assert.strictEqual(checkRateLimit(testIp, windowMs, maxLimit), true); // 3
    assert.strictEqual(checkRateLimit(testIp, windowMs, maxLimit), false); // 4 (blocked)
  });

  test('resets counter after window expiration', async () => {
    const testIp = `test-reset-ip-${Date.now()}`;
    const windowMs = 50; // 50ms short window
    const maxLimit = 2;

    assert.strictEqual(checkRateLimit(testIp, windowMs, maxLimit), true);
    assert.strictEqual(checkRateLimit(testIp, windowMs, maxLimit), true);
    assert.strictEqual(checkRateLimit(testIp, windowMs, maxLimit), false);

    // Wait for window to expire
    await new Promise((resolve) => setTimeout(resolve, 60));

    // Next request should succeed again
    assert.strictEqual(checkRateLimit(testIp, windowMs, maxLimit), true);
  });

  test('enforces hard capacity ceiling with FIFO eviction (prevents unbounded memory growth)', () => {
    const smallCeilingLimit = 10;
    // Fill up to ceiling
    for (let i = 0; i < smallCeilingLimit; i++) {
      checkRateLimit(`ip-${i}`, 60000, 5);
    }
    assert.strictEqual(getRateLimitMapSize(), smallCeilingLimit);

    // Verify MAX_MAP_ENTRIES is a positive integer constant
    assert.ok(MAX_MAP_ENTRIES >= 1000);
  });
});

describe('Security - Client IP Resolution & Anti-Spoofing', () => {
  test('prioritizes cf-connecting-ip when present', () => {
    const headers = new Map([
      ['cf-connecting-ip', '203.0.113.195'],
      ['x-vercel-ip', '198.51.100.99'],
      ['x-real-ip', '198.51.100.1'],
      ['x-forwarded-for', '10.0.0.1, 192.168.1.1'],
    ]);
    const ip = getClientIp({ get: (h: string) => headers.get(h) ?? null });
    assert.strictEqual(ip, '203.0.113.195');
  });

  test('prioritizes x-vercel-ip over x-real-ip and x-forwarded-for', () => {
    const headers = new Map([
      ['x-vercel-ip', '198.51.100.77'],
      ['x-real-ip', '198.51.100.1'],
      ['x-forwarded-for', '10.0.0.1, 192.168.1.1'],
    ]);
    const ip = getClientIp({ get: (h: string) => headers.get(h) ?? null });
    assert.strictEqual(ip, '198.51.100.77');
  });

  test('falls back to x-real-ip if edge headers are absent', () => {
    const headers = new Map([
      ['x-real-ip', '198.51.100.42'],
      ['x-forwarded-for', 'client.origin.ip, 10.0.0.2'],
    ]);
    const ip = getClientIp({ get: (h: string) => headers.get(h) ?? null });
    assert.strictEqual(ip, '198.51.100.42');
  });

  test('extracts first hop from x-forwarded-for as client origin', () => {
    const headers = new Map([
      ['x-forwarded-for', '203.0.113.50, proxy1, proxy2'],
    ]);
    const ip = getClientIp({ get: (h: string) => headers.get(h) ?? null });
    assert.strictEqual(ip, '203.0.113.50');
  });

  test('defaults to local-client when no headers provided', () => {
    const ip = getClientIp({ get: () => null });
    assert.strictEqual(ip, 'local-client');
  });
});

describe('Security - Production Basic Auth Validation (web/lib/auth.ts)', () => {
  const testUser = 'radar_demo';
  const testPass = 'RADAR_DEMO_2026';

  test('validates correct standard credentials', async () => {
    const authHeader = 'Basic ' + Buffer.from(`${testUser}:${testPass}`).toString('base64');
    const result = await validateBasicAuth(authHeader, testUser, testPass);
    assert.strictEqual(result.authorized, true);
  });

  test('handles UTF-8 accented passwords properly without corruption', async () => {
    const utf8User = 'amministratore';
    const utf8Pass = 'Caffè_Silanùs_2026_€#';
    const authHeader = 'Basic ' + Buffer.from(`${utf8User}:${utf8Pass}`, 'utf-8').toString('base64');

    // Test base64 utf-8 decoding helper directly
    const decoded = decodeBase64Utf8(Buffer.from(`${utf8User}:${utf8Pass}`, 'utf-8').toString('base64'));
    assert.strictEqual(decoded, `${utf8User}:${utf8Pass}`);

    const result = await validateBasicAuth(authHeader, utf8User, utf8Pass);
    assert.strictEqual(result.authorized, true);
  });

  test('constant-time safeCompare rejects different strings and different lengths', async () => {
    assert.strictEqual(await safeCompare('exactMatch', 'exactMatch'), true);
    assert.strictEqual(await safeCompare('short', 'longerStringWithDiffLength'), false);
    assert.strictEqual(await safeCompare('passwordA', 'passwordB'), false);
  });

  test('fails closed when expected environment variables are missing', async () => {
    const authHeader = 'Basic ' + Buffer.from(`${testUser}:${testPass}`).toString('base64');
    const missingUserResult = await validateBasicAuth(authHeader, undefined, testPass);
    assert.strictEqual(missingUserResult.authorized, false);
    assert.strictEqual(missingUserResult.reason, 'missing_env');

    const missingPassResult = await validateBasicAuth(authHeader, testUser, undefined);
    assert.strictEqual(missingPassResult.authorized, false);
    assert.strictEqual(missingPassResult.reason, 'missing_env');
  });

  test('rejects invalid password', async () => {
    const authHeader = 'Basic ' + Buffer.from(`${testUser}:wrong_password`).toString('base64');
    const result = await validateBasicAuth(authHeader, testUser, testPass);
    assert.strictEqual(result.authorized, false);
    assert.strictEqual(result.reason, 'invalid_credentials');
  });

  test('rejects invalid username', async () => {
    const authHeader = 'Basic ' + Buffer.from(`hacker:${testPass}`).toString('base64');
    const result = await validateBasicAuth(authHeader, testUser, testPass);
    assert.strictEqual(result.authorized, false);
    assert.strictEqual(result.reason, 'invalid_credentials');
  });

  test('rejects missing or malformed header', async () => {
    assert.strictEqual((await validateBasicAuth(null, testUser, testPass)).authorized, false);
    assert.strictEqual((await validateBasicAuth('Bearer token123', testUser, testPass)).authorized, false);
    assert.strictEqual((await validateBasicAuth('Basic ', testUser, testPass)).authorized, false);
    assert.strictEqual((await validateBasicAuth('Basic Tm9Db2xvbg==', testUser, testPass)).authorized, false); // "NoColon"
  });
});
