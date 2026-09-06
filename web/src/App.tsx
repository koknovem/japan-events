import { useEffect, useMemo, useState } from 'react'
import { format, parseISO } from 'date-fns'
import { useTranslation } from 'react-i18next'
import { AppShell } from './components/layout/AppShell'
import { DateCalendar } from './components/calendar/DateCalendar'
import { EventList } from './components/events/EventList'
import { EventsPanelHeader } from './components/events/EventsPanelHeader'
import { PrefectureFilter } from './components/events/PrefectureFilter'
import { useCachedDates, useEventsForDate, useSites } from './hooks/useEvents'

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

  const [selected, setSelected] = useState<Date>(() => new Date())
  const [month, setMonth] = useState<Date>(() => new Date())
  const [prefecture, setPrefecture] = useState<string | null>(null)
  const [bootstrapped, setBootstrapped] = useState(false)

  useEffect(() => {
    if (bootstrapped || dates.length === 0) return
    const d = defaultDate(dates)
    setSelected(d)
    setMonth(d)
    setBootstrapped(true)
  }, [dates, bootstrapped])

  const { data, loading, scraping, refreshing, progress, error, dateKey } = useEventsForDate(
    selected,
    prefecture,
    cachedSet,
    datesReady,
  )

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
            data={data}
            error={error}
            loading={loading}
            scraping={scraping}
            refreshing={refreshing}
            progress={progress}
          />
          {refreshing && progress && !loading ? (
            <div className="refresh-strip" aria-live="polite">
              <div
                className="refresh-strip-fill"
                style={{ width: `${Math.max(4, progress.percent ?? 0)}%` }}
              />
            </div>
          ) : null}
          <EventList
            events={data?.events ?? []}
            loading={loading}
            scraping={scraping}
            progress={progress}
            dateLabel={format(selected, 'yyyy-MM-dd')}
            emptyMessage={
              data?.message ?? t('events.emptyMessage', { date: dateKey })
            }
          />
        </main>
      </div>
    </AppShell>
  )
}
