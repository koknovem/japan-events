import { useEffect, useMemo, useRef, useState } from 'react'
import { parseISO } from 'date-fns'
import { useTranslation } from 'react-i18next'
import { AppShell } from './components/layout/AppShell'
import { DateCalendar } from './components/calendar/DateCalendar'
import { EventList } from './components/events/EventList'
import { EventsPanelHeader } from './components/events/EventsPanelHeader'
import { PrefectureFilter } from './components/events/PrefectureFilter'
import { useCachedDates, useEventsForDate, useScrapeStatus, useSites } from './hooks/useEvents'
import { eventsOnDate } from './lib/eventOnDate'

function defaultDate(cached: string[]): Date {
  if (cached.includes('2026-09-06')) return parseISO('2026-09-06')
  if (cached.length > 0) return parseISO(cached[cached.length - 1])
  return new Date()
}

export default function App() {
  const { t } = useTranslation()
  const { sites } = useSites()
  const { dates, refresh: refreshDates, ready: datesReady } = useCachedDates()
  const cachedSet = useMemo(() => new Set(dates), [dates])
  const scrapeStatus = useScrapeStatus()
  const inflightDates = useMemo(
    () => new Set(scrapeStatus?.inflight_dates ?? []),
    [scrapeStatus?.inflight_dates],
  )
  const queuedDates = useMemo(
    () => new Set(scrapeStatus?.queued_dates ?? []),
    [scrapeStatus?.queued_dates],
  )
  const runningDates = useMemo(
    () => new Set(scrapeStatus?.running_dates ?? []),
    [scrapeStatus?.running_dates],
  )

  const [selected, setSelected] = useState<Date>(() => new Date())
  const [month, setMonth] = useState<Date>(() => new Date())
  const [prefecture, setPrefecture] = useState<string | null>(null)
  const [bootstrapped, setBootstrapped] = useState(false)
  const prevInflight = useRef<string[]>([])

  useEffect(() => {
    if (bootstrapped || !datesReady) return
    const d = defaultDate(dates)
    setSelected(d)
    setMonth(d)
    setBootstrapped(true)
  }, [dates, datesReady, bootstrapped])

  const { data, loading, scraping, refreshing, progress, error, dateKey } = useEventsForDate(
    selected,
    prefecture,
    datesReady && bootstrapped,
  )
  const dateData = data?.date === dateKey ? data : null
  const visibleEvents = eventsOnDate(dateData?.events ?? [], dateKey)

  useEffect(() => {
    const current = scrapeStatus?.inflight_dates ?? []
    const left = prevInflight.current.filter((item) => !current.includes(item))
    prevInflight.current = current
    if (left.length > 0) void refreshDates()
  }, [scrapeStatus?.inflight_dates, refreshDates])

  useEffect(() => {
    if (data?.scraped) {
      void refreshDates()
    }
  }, [data?.scraped, refreshDates])

  return (
    <AppShell>
      <div className="workspace">
        <aside>
          <DateCalendar
            selected={selected}
            onSelect={(day) => {
              setSelected(day)
              setMonth(day)
            }}
            month={month}
            onMonthChange={setMonth}
            cachedDates={cachedSet}
            runningDates={runningDates.size > 0 ? runningDates : inflightDates}
            queuedDates={queuedDates}
          />
          <div style={{ marginTop: '0.85rem' }} className="panel panel-calendar">
            <PrefectureFilter sites={sites} value={prefecture} onChange={setPrefecture} />
            <p style={{ margin: '0.85rem 0 0', color: 'var(--muted)', fontSize: '0.8rem', lineHeight: 1.45 }}>
              {t('hint.cacheDots')}
            </p>
          </div>
        </aside>

        <main className="panel panel-events">
          <EventsPanelHeader
            date={selected}
            data={dateData ? { ...dateData, events: visibleEvents, event_count: visibleEvents.length } : null}
            error={error}
            loading={loading}
            scraping={scraping}
            refreshing={refreshing}
            progress={progress}
          />
          {(scraping || refreshing) && progress && visibleEvents.length > 0 ? (
            <div className="refresh-strip" aria-live="polite">
              <div
                className="refresh-strip-fill"
                style={{ width: `${Math.max(4, progress.percent ?? 0)}%` }}
              />
            </div>
          ) : null}
          <EventList
            events={visibleEvents}
            loading={loading}
            scraping={scraping}
            progress={progress}
            dateLabel={dateKey}
            emptyMessage={
              dateData?.message ?? t('events.emptyMessage', { date: dateKey })
            }
          />
        </main>
      </div>
    </AppShell>
  )
}
