import { useCallback, useEffect, useState } from 'react'
import { format } from 'date-fns'
import { useTranslation } from 'react-i18next'
import { api } from '../api/client'
import type { EventsResponse, LoadProgress, ScrapeJob, ScrapeStatus, Site } from '../types/events'

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

export function useScrapeStatus() {
  const [status, setStatus] = useState<ScrapeStatus | null>(null)

  useEffect(() => {
    let alive = true
    let timer: number | undefined
    const tick = async () => {
      try {
        const next = await api.scrapeStatus()
        if (!alive) return
        setStatus(next)
        const busy = (next.inflight_dates?.length ?? 0) > 0
        timer = window.setTimeout(() => {
          void tick()
        }, busy ? 800 : 15_000)
      } catch {
        if (!alive) return
        timer = window.setTimeout(() => {
          void tick()
        }, 15_000)
      }
    }
    void tick()
    return () => {
      alive = false
      if (timer !== undefined) window.clearTimeout(timer)
    }
  }, [])

  return status
}

function jobToProgress(job: ScrapeJob, status?: ScrapeStatus | null): LoadProgress {
  const queued = Boolean(job.queued) || job.phase === 'queued'
  return {
    mode: 'scrape',
    date: job.date,
    percent: queued ? null : job.percent,
    done: job.done,
    total: job.total,
    okCount: job.ok_count,
    eventsSoFar: job.events_so_far,
    running: job.running,
    sites: job.sites,
    phase: queued ? 'queued' : job.phase,
    concurrency: job.concurrency,
    queued,
    workers: status?.workers,
    inflightDates: status?.inflight_dates ?? [],
    runningDates: status?.running_dates ?? [],
  }
}

const scrapeStart = (date: string): LoadProgress => ({
  mode: 'scrape',
  date,
  percent: null,
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

function isAbort(err: unknown): boolean {
  return err instanceof DOMException && err.name === 'AbortError'
}

export function useEventsForDate(
  selected: Date,
  prefectureFilter: string | null,
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
  const reload = useCallback(() => {
    setReloadToken((value) => value + 1)
  }, [])

  useEffect(() => {
    if (!datesReady) return

    const controller = new AbortController()
    let cancelled = false
    const eventOpts = {
      prefecture: prefectureFilter ?? undefined,
      lang,
    }

    setLoading(true)
    setError(null)
    setRefreshing(false)
    setScraping(false)
    setProgress(downloadStart(dateKey))
    setData((prev) => (prev?.date === dateKey ? prev : null))

    const sleep = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms))

    const followJob = async (initial?: ScrapeStatus) => {
      let sawInflight = Boolean(initial?.inflight_dates.includes(dateKey))
      let lastDone = -1
      if (initial?.job) setProgress(jobToProgress(initial.job, initial))

      const pullPartial = async (job: ScrapeJob | undefined) => {
        const done = job?.done ?? 0
        if (done === lastDone || done <= 0) return
        lastDone = done
        const latest = await api.events(dateKey, eventOpts, { signal: controller.signal })
        if (cancelled || latest.date !== dateKey) return
        setData(latest)
        if ((latest.events?.length ?? 0) > 0) setLoading(false)
      }

      while (!cancelled) {
        try {
          const status = await api.scrapeStatus(undefined, { signal: controller.signal })
          const job = status.jobs.find((item) => item.date === dateKey) ?? status.job
          const inFlight = status.inflight_dates.includes(dateKey)
          if (inFlight) sawInflight = true
          if (job) setProgress(jobToProgress(job, status))
          await pullPartial(job)

          if (job?.phase === 'error') {
            throw new Error(job.error || t('events.loadError'))
          }

          const finished = (sawInflight && !inFlight) || job?.phase === 'done'
          if (finished) {
            const latest = await api.events(dateKey, eventOpts, { signal: controller.signal })
            if (cancelled || latest.date !== dateKey) return
            if (latest.scraping) {
              sawInflight = true
              await sleep(700)
              continue
            }
            setData(latest)
            setScraping(false)
            setRefreshing(false)
            setLoading(false)
            setProgress(null)
            return
          }
        } catch (err) {
          if (isAbort(err) || cancelled) return
          throw err
        }
        await sleep(700)
      }
    }

    const followBackgroundRefresh = async () => {
      let sawJob = false
      let lastDone = -1
      const giveUpAt = Date.now() + 20_000
      while (!cancelled) {
        try {
          const status = await api.scrapeStatus(dateKey, { signal: controller.signal })
          const job = status.job
          const inFlight = status.inflight_dates.includes(dateKey)
          const active =
            inFlight ||
            (!!job && ['starting', 'queued', 'scanning', 'scraping', 'combining'].includes(job.phase))
          if (active) {
            sawJob = true
            setRefreshing(true)
            if (job) setProgress(jobToProgress(job, status))
            const done = job?.done ?? 0
            if (done !== lastDone && done > 0) {
              lastDone = done
              const latest = await api.events(dateKey, eventOpts, { signal: controller.signal })
              if (!cancelled && latest.date === dateKey) {
                setData({ ...latest, refreshing: true })
                if ((latest.events?.length ?? 0) > 0) setLoading(false)
              }
            }
          } else if (sawJob) {
            const latest = await api.events(dateKey, eventOpts, { signal: controller.signal })
            if (!cancelled && latest.date === dateKey) {
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
          if (isAbort(err) || cancelled) return
        }
        await sleep(700)
      }
    }

    void (async () => {
      try {
        const res = await api.events(dateKey, eventOpts, {
          signal: controller.signal,
          onDownloadProgress: (loaded, total) => {
            if (cancelled) return
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
        if (cancelled) return

        if (res.date !== dateKey) return

        if (res.scraping) {
          setScraping(true)
          setProgress(scrapeStart(dateKey))
          setData(res)
          if ((res.events?.length ?? 0) > 0) setLoading(false)
          const status = await api.scrapeStatus(undefined, { signal: controller.signal })
          await followJob(status)
          return
        }

        setData(res)
        setScraping(false)
        setLoading(false)
        setProgress(null)
        if (res.refreshing) {
          setRefreshing(true)
          await followBackgroundRefresh()
        }
      } catch (err) {
        if (cancelled || isAbort(err)) return
        setError(err instanceof Error ? err.message : t('events.loadError'))
        setData(null)
        setLoading(false)
        setScraping(false)
        setRefreshing(false)
        setProgress(null)
      }
    })()

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [dateKey, prefectureFilter, lang, t, reloadToken, datesReady])

  return {
    data,
    loading,
    scraping,
    refreshing,
    progress: progress?.date === dateKey ? progress : null,
    error,
    reload,
    dateKey,
  }
}
