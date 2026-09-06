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
}
