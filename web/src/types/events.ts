export interface Site {
  id: string
  name: string
  region: string
  home_url: string
  event_url: string | null
  source_org: string | null
  adapter: string
}

export interface EventItem {
  prefecture: string
  title: string
  start_date: string | null
  end_date: string | null
  start_time: string | null
  end_time: string | null
  venue: string | null
  area: string | null
  category: string | null
  description: string | null
  url: string | null
  image_url: string | null
  source: string
  lang?: string
  site_id: string | null
}

export interface SiteStatus {
  id: string
  prefecture: string
  ok: boolean
  event_count: number
  error: string | null
  notes: string | null
  source_url: string | null
  adapter: string | null
}

export interface EventsResponse {
  date: string
  cached: boolean
  scraped?: boolean
  generated_at: string | null
  site_count: number
  ok_count: number
  event_count: number
  events: EventItem[]
  sites: SiteStatus[]
  message: string | null
  refreshing?: boolean
  scraping?: boolean
}

export interface ScrapeSiteProgress {
  id: string
  prefecture: string
  status: 'pending' | 'running' | 'ok' | 'error' | string
  event_count: number
  error: string | null
}

export interface ScrapeJob {
  date: string
  phase: 'starting' | 'queued' | 'scraping' | 'combining' | 'done' | 'error' | string
  total: number
  done: number
  ok_count: number
  events_so_far: number
  percent: number
  running: string[]
  sites: ScrapeSiteProgress[]
  error: string | null
  concurrency?: number
  queued?: boolean
}

export interface ScrapeStatus {
  inflight_dates: string[]
  running_dates?: string[]
  queued_dates?: string[]
  workers: number
  job: ScrapeJob | null
  jobs: ScrapeJob[]
}

export interface LoadProgress {
  mode: 'scrape' | 'download'
  date?: string
  percent: number | null
  done: number
  total: number
  okCount: number
  eventsSoFar: number
  running: string[]
  sites: ScrapeSiteProgress[]
  phase: string
  concurrency?: number
  loadedBytes?: number
  totalBytes?: number
  queued?: boolean
  workers?: number
  inflightDates?: string[]
  runningDates?: string[]
}
