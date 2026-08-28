// Server-side fetch against the FastAPI backend. No screen calls fetch directly.

export const API_BASE = process.env.NEEV_API_BASE ?? 'http://127.0.0.1:8000';

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { 'content-type': 'application/json', ...(init?.headers ?? {}) },
    // Loan data is private and changes on every decision; never cache it.
    cache: 'no-store',
  });
  if (!response.ok) {
    throw new ApiError(
      `${init?.method ?? 'GET'} ${path} failed: ${response.status}`,
      response.status
    );
  }
  return (await response.json()) as T;
}

export function apiGet<T>(path: string): Promise<T> {
  return request<T>(path);
}

export function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined });
}
