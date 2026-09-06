import { useCallback, useEffect, useState } from 'react'
import { format } from 'date-fns'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import type { EventsResponse, LoadProgress, ScrapeJob, Site } from '../types/events'

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
  const [ready, setReady] = useState(false)
  const refresh = useCallback(async () => {
    const data = await api.dates()
    setDates(data.dates)
  }, [])

  useEffect(() => {
    void refresh()
      .catch(() => setDates([]))
      .finally(() => setReady(true))
  }, [refresh])

  return { dates, refresh, ready }
}

function jobToProgress(job: ScrapeJob): LoadProgress {
  return {
    mode: 'scrape',
    date: job.date,
    percent: job.percent,
    done: job.done,
    total: job.total,
    okCount: job.ok_count,
    eventsSoFar: job.events_so_far,
    running: job.running,
    sites: job.sites,
    phase: job.phase,
    concurrency: job.concurrency,
  }
}

const scrapeStart = (date: string): LoadProgress => ({
  mode: 'scrape',
  date,
  percent: 0,
  done: 0,
  total: 0,
  okCount: 0,
  eventsSoFar: 0,
  running: [],
  sites: [],
  phase: 'starting',
})

const downloadStart = (date: string): LoadProgress => ({
  mode: 'download',
  date,
  percent: null,
  done: 0,
  total: 0,
  okCount: 0,
  eventsSoFar: 0,
  running: [],
  sites: [],
  phase: 'download',
})

export function useEventsForDate(
  selected: Date,
  prefectureFilter: string | null,
  cachedDates: Set<string>,
  datesReady: boolean,
) {
  const { t, i18n } = useTranslation()
  const [data, setData] = useState<EventsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [scraping, setScraping] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [progress, setProgress] = useState<LoadProgress | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [reloadToken, setReloadToken] = useState(0)
  const dateKey = format(selected, 'yyyy-MM-dd')
  const lang = i18n.language
  const isCached = cachedDates.has(dateKey)
  const reload = useCallback(() => {
    setReloadToken((value) => value + 1)
  }, [])

  useEffect(() => {
    if (!datesReady) return

    const controller = new AbortController()
    const willScrape = !isCached
    let pollTimer: number | undefined
    let cancelled = false
    const eventOpts = {
      prefecture: prefectureFilter ?? undefined,
      lang,
    }

    setLoading(true)
    setError(null)
    setRefreshing(false)
    setScraping(willScrape)
    setProgress(willScrape ? scrapeStart(dateKey) : downloadStart(dateKey))

    const pollStatus = async () => {
      try {
        const status = await api.scrapeStatus(dateKey, { signal: controller.signal })
        if (!cancelled && status.job) setProgress(jobToProgress(status.job))
      } catch (err) {
        if (err instanceof DOMException && err.name === 'AbortError') return
      }
    }

    const sleep = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms))

    const followBackgroundRefresh = async () => {
      let sawJob = false
      const giveUpAt = Date.now() + 20_000
      while (!cancelled) {
        try {
          const status = await api.scrapeStatus(dateKey, { signal: controller.signal })
          const job = status.job
          const inFlight = status.inflight_dates.includes(dateKey)
          const active =
            inFlight ||
            (!!job && ['starting', 'scanning', 'scraping', 'combining'].includes(job.phase))
          if (active) {
            sawJob = true
            setRefreshing(true)
            if (job) setProgress(jobToProgress(job))
          } else if (sawJob) {
            const latest = await api.events(dateKey, eventOpts, { signal: controller.signal })
            if (!cancelled) {
              setData({ ...latest, refreshing: false })
              setRefreshing(false)
              setProgress(null)
            }
            return
          } else if (Date.now() > giveUpAt) {
            if (!cancelled) {
              setRefreshing(false)
              setProgress(null)
            }
            return
          }
        } catch (err) {
          if (err instanceof DOMException && err.name === 'AbortError') return
        }
        await sleep(700)
      }
    }

    void (async () => {
      try {
        const eventsPromise = api.events(dateKey, eventOpts, {
          signal: controller.signal,
          onDownloadProgress: (loaded, total) => {
            if (cancelled || willScrape) return
            setProgress({
              mode: 'download',
              date: dateKey,
              percent: total > 0 ? Math.min(99, Math.round((loaded * 100) / total)) : null,
              done: loaded,
              total,
              okCount: 0,
              eventsSoFar: 0,
              running: [],
              sites: [],
              phase: 'download',
              loadedBytes: loaded,
              totalBytes: total,
            })
          },
        })

        if (willScrape) {
          void pollStatus()
          pollTimer = window.setInterval(() => {
            void pollStatus()
          }, 700)
        }

        const res = await eventsPromise
        if (cancelled) return
        setData(res)
        setScraping(Boolean(res.scraped))
        setLoading(false)
        if (willScrape) {
          setProgress(null)
          setScraping(false)
          return
        }
        setProgress(null)
        if (res.refreshing) {
          setRefreshing(true)
          await followBackgroundRefresh()
        }
      } catch (err) {
        if (cancelled || (err instanceof DOMException && err.name === 'AbortError')) return
        setError(err instanceof Error ? err.message : t('events.loadError'))
        setData(null)
        setLoading(false)
        setScraping(false)
        setRefreshing(false)
        setProgress(null)
      } finally {
        if (pollTimer !== undefined) window.clearInterval(pollTimer)
      }
    })()

    return () => {
      cancelled = true
      controller.abort()
      if (pollTimer !== undefined) window.clearInterval(pollTimer)
    }
  }, [dateKey, prefectureFilter, lang, t, reloadToken, datesReady, isCached])

  return {
    data,
    loading,
    scraping: scraping && !isCached,
    refreshing,
    progress: progress?.date === dateKey ? progress : null,
    error,
    reload,
    dateKey,
  }
}

