import type { EventsResponse, ScrapeStatus, Site } from '../types/events'

const BASE = ''

type RequestOpts = RequestInit & {
  onDownloadProgress?: (loaded: number, total: number) => void
}

async function request<T>(path: string, init?: RequestOpts): Promise<T> {
  const { onDownloadProgress, ...rest } = init ?? {}
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(rest.headers ?? {}) },
    ...rest,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error((body as { detail?: string }).detail ?? `HTTP ${res.status}`)
  }
  if (!onDownloadProgress || !res.body) {
    return res.json() as Promise<T>
  }

  const total = Number(res.headers.get('content-length') || 0)
  const reader = res.body.getReader()
  const chunks: Uint8Array[] = []
  let loaded = 0
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    if (!value) continue
    chunks.push(value)
    loaded += value.byteLength
    onDownloadProgress(loaded, total)
  }

  const bytes = new Uint8Array(loaded)
  let offset = 0
  for (const chunk of chunks) {
    bytes.set(chunk, offset)
    offset += chunk.byteLength
  }
  return JSON.parse(new TextDecoder().decode(bytes)) as T
}

export const api = {
  health: () => request<{ status: string; version: string }>('/api/health'),
  sites: () => request<Site[]>('/api/sites'),
  dates: () => request<{ dates: string[] }>('/api/dates'),
  scrapeStatus: (date?: string, init?: RequestInit) => {
    const params = new URLSearchParams()
    if (date) params.set('date', date)
    const query = params.toString()
    return request<ScrapeStatus>(`/api/scrape/status${query ? `?${query}` : ''}`, init)
  },
  events: (
    date: string,
    opts?: { prefecture?: string; lang?: string },
    init?: RequestOpts,
  ) => {
    const params = new URLSearchParams({ date })
    if (opts?.prefecture) params.set('prefecture', opts.prefecture)
    if (opts?.lang) params.set('lang', opts.lang)
    return request<EventsResponse>(`/api/events?${params}`, init)
  },
}
