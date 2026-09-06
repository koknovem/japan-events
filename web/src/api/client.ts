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
  events: (date: string, prefecture?: string) => {
    const params = new URLSearchParams({ date })
    if (prefecture) params.set('prefecture', prefecture)
    return request<EventsResponse>(`/api/events?${params}`)
  },
}
