import { useCallback, useEffect, useState } from 'react'
import { format } from 'date-fns'
import { useTranslation } from 'react-i18next'
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
  const { t, i18n } = useTranslation()
  const [data, setData] = useState<EventsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [scraping, setScraping] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const dateKey = format(selected, 'yyyy-MM-dd')
  const lang = i18n.language

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    setScraping(!cachedDates.has(dateKey))
    try {
      const res = await api.events(dateKey, {
        prefecture: prefectureFilter ?? undefined,
        lang,
      })
      setData(res)
      setScraping(Boolean(res.scraped))
    } catch (err) {
      setError(err instanceof Error ? err.message : t('events.loadError'))
      setData(null)
    } finally {
      setLoading(false)
      setScraping(false)
    }
  }, [dateKey, prefectureFilter, cachedDates, t, lang])

  useEffect(() => {
    void load()
  }, [load])

  return { data, loading, scraping, error, reload: load, dateKey }
}
