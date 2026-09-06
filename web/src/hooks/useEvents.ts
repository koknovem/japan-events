import { useCallback, useEffect, useState } from 'react'
import { format } from 'date-fns'
import { api } from '../api/client'
import type { EventsResponse, Site } from '../types/events'

export function useSites() {
  const [sites, setSites] = useState<Site[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    api
      .sites()
      .then((data) => {
        if (alive) setSites(data)
      })
      .catch((err: Error) => {
        if (alive) setError(err.message)
      })
    return () => {
      alive = false
    }
  }, [])

  return { sites, error }
}

export function useCachedDates() {
  const [dates, setDates] = useState<string[]>([])
  const refresh = useCallback(async () => {
    const data = await api.dates()
    setDates(data.dates)
  }, [])

  useEffect(() => {
    void refresh().catch(() => setDates([]))
  }, [refresh])

  return { dates, refresh }
}

export function useEventsForDate(
  selected: Date,
  prefectureFilter: string | null,
  cachedDates: Set<string>,
) {
  const [data, setData] = useState<EventsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [scraping, setScraping] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const dateKey = format(selected, 'yyyy-MM-dd')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    setScraping(!cachedDates.has(dateKey))
    try {
      const res = await api.events(dateKey, prefectureFilter ?? undefined)
      setData(res)
      setScraping(Boolean(res.scraped))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load events')
      setData(null)
    } finally {
      setLoading(false)
      setScraping(false)
    }
  }, [dateKey, prefectureFilter, cachedDates])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    if (data?.cached || data?.scraped) {
      // refresh green dots after a fresh scrape
    }
  }, [data])

  return { data, loading, scraping, error, reload: load, dateKey }
}
