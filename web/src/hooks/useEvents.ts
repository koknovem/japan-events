import { useCallback, useEffect, useRef, useState } from 'react'
import { format } from 'date-fns'
import { api } from '../api/client'
import type { EventsResponse, ScrapeJob, Site } from '../types/events'

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

export function useEventsForDate(selected: Date, prefectureFilter: string | null) {
  const [data, setData] = useState<EventsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const dateKey = format(selected, 'yyyy-MM-dd')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.events(dateKey, prefectureFilter ?? undefined)
      setData(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load events')
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [dateKey, prefectureFilter])

  useEffect(() => {
    void load()
  }, [load])

  return { data, loading, error, reload: load, dateKey }
}

export function useScrapeJob() {
  const [job, setJob] = useState<ScrapeJob | null>(null)
  const [busy, setBusy] = useState(false)
  const timer = useRef<number | null>(null)

  const clearTimer = () => {
    if (timer.current != null) {
      window.clearInterval(timer.current)
      timer.current = null
    }
  }

  useEffect(() => () => clearTimer(), [])

  const start = useCallback(async (date: string, prefecture?: string | null) => {
    setBusy(true)
    clearTimer()
    try {
      const started = await api.startScrape(date, prefecture ?? undefined)
      setJob(started)
      timer.current = window.setInterval(async () => {
        try {
          const next = await api.scrapeStatus(started.id)
          setJob(next)
          if (next.status === 'completed' || next.status === 'failed') {
            clearTimer()
            setBusy(false)
          }
        } catch {
          clearTimer()
          setBusy(false)
        }
      }, 2000)
    } catch (err) {
      setBusy(false)
      throw err
    }
  }, [])

  return { job, busy, start }
}
