import type { ChatRequest, ChatResponse, SourceRecord } from './types';
import { requestJson } from './apiRequest.js';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export const api = {
  health: () => requestJson<{ status: string; service: string; version: string }>(API_BASE_URL, '/health'),
  getSources: () => requestJson<{ sources: SourceRecord[] }>(API_BASE_URL, '/api/v1/sources'),
  postChat: (payload: ChatRequest) => requestJson<ChatResponse>(API_BASE_URL, '/api/v1/chat', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
};
