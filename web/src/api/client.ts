import type { EventsResponse, Site } from '../types/events'

const BASE = ''

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () => request<{ status: string; version: string }>('/api/health'),
  sites: () => request<Site[]>('/api/sites'),
  dates: () => request<{ dates: string[] }>('/api/dates'),
  events: (date: string, opts?: { prefecture?: string; lang?: string }) => {
    const params = new URLSearchParams({ date })
    if (opts?.prefecture) params.set('prefecture', opts.prefecture)
    if (opts?.lang) params.set('lang', opts.lang)
    return request<EventsResponse>(`/api/events?${params}`)
  },
}
