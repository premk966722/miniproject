export async function requestJson(baseUrl, path, init = {}) {
  const headers = { ...(init.headers || {}) };
  if (init.body !== undefined && !Object.keys(headers).some((key) => key.toLowerCase() === 'content-type')) {
    headers['Content-Type'] = 'application/json';
  }
  const response = await fetch(`${baseUrl.replace(/\/+$/, '')}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    let message = `Request failed with ${response.status}`;
    try {
      const payload = await response.json();
      if (payload?.error?.message) {
        message = payload.error.message;
      } else if (payload?.detail?.message) {
        message = payload.detail.message;
      } else if (typeof payload?.detail === 'string') {
        message = payload.detail;
      } else if (payload?.message) {
        message = payload.message;
      }
    } catch {
      // Keep the status-based message when the server returned a non-JSON error.
    }
    throw new Error(message);
  }

  return response.json();
}
