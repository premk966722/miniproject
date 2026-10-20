import assert from 'node:assert/strict';
import test from 'node:test';
import { requestJson } from '../src/apiRequest.js';


test('requestJson joins URL, preserves custom headers, and parses JSON', async () => {
  const originalFetch = globalThis.fetch;
  let captured;
  globalThis.fetch = async (url, init) => {
    captured = { url, init };
    return new Response(JSON.stringify({ status: 'ok' }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  };
  try {
    const result = await requestJson('https://api.example.test/', '/health', {
      headers: { 'x-trace-id': 'trace-1' },
    });
    assert.deepEqual(result, { status: 'ok' });
    assert.equal(captured.url, 'https://api.example.test/health');
    assert.equal(captured.init.headers['Content-Type'], undefined);
    assert.equal(captured.init.headers['x-trace-id'], 'trace-1');
  } finally {
    globalThis.fetch = originalFetch;
  }
});


test('requestJson surfaces structured backend error messages', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => new Response(JSON.stringify({
    error: { code: 'invalid_request', message: 'Request validation failed.' },
  }), { status: 422, headers: { 'Content-Type': 'application/json' } });
  try {
    await assert.rejects(
      requestJson('http://localhost:8000', '/api/v1/chat'),
      { message: 'Request validation failed.' },
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});
