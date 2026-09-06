import {
  addMonths,
  eachDayOfInterval,
  endOfMonth,
  endOfWeek,
  format,
  isSameDay,
  isSameMonth,
  isToday,
  startOfMonth,
  startOfWeek,
  subMonths,
} from 'date-fns'
import { useTranslation } from 'react-i18next'
import { dateFnsLocales, type AppLang } from '../../i18n'

interface DateCalendarProps {
  selected: Date
  onSelect: (day: Date) => void
  month: Date
  onMonthChange: (month: Date) => void
  cachedDates: Set<string>
  runningDates?: Set<string>
  queuedDates?: Set<string>
}

export function DateCalendar({
  selected,
  onSelect,
  month,
  onMonthChange,
  cachedDates,
  runningDates,
  queuedDates,
}: DateCalendarProps) {
  const { t, i18n } = useTranslation()
  const lang = (i18n.language as AppLang) in dateFnsLocales ? (i18n.language as AppLang) : 'en'
  const locale = dateFnsLocales[lang]
  const weekdays = t('calendar.weekdays', { returnObjects: true }) as string[]

  const monthStart = startOfMonth(month)
  const days = eachDayOfInterval({
    start: startOfWeek(monthStart, { locale }),
    end: endOfWeek(endOfMonth(monthStart), { locale }),
  })

  return (
    <section className="panel panel-calendar" aria-label={t('calendar.ariaLabel')}>
      <div className="calendar-nav">
        <button
          type="button"
          className="btn btn-ghost"
          aria-label={t('calendar.prevMonth')}
          onClick={() => onMonthChange(subMonths(month, 1))}
        >
          ‹
        </button>
        <h3>{format(month, 'MMMM yyyy', { locale })}</h3>
        <button
          type="button"
          className="btn btn-ghost"
          aria-label={t('calendar.nextMonth')}
          onClick={() => onMonthChange(addMonths(month, 1))}
        >
          ›
        </button>
      </div>

      <div className="calendar-weekdays" aria-hidden>
        {weekdays.map((d) => (
          <span key={d}>{d}</span>
        ))}
      </div>

      <div className="calendar-grid" role="grid" aria-label={format(month, 'MMMM yyyy', { locale })}>
        {days.map((day) => {
          const key = format(day, 'yyyy-MM-dd')
          const inMonth = isSameMonth(day, month)
          const selectedDay = isSameDay(day, selected)
          const classes = [
            'day-cell',
            inMonth ? '' : 'is-outside',
            selectedDay ? 'is-selected' : '',
            isToday(day) ? 'is-today' : '',
            cachedDates.has(key) ? 'has-cache' : '',
            runningDates?.has(key) ? 'is-scraping' : '',
            queuedDates?.has(key) && !runningDates?.has(key) ? 'is-queued' : '',
          ]
            .filter(Boolean)
            .join(' ')

          return (
            <button
              key={key}
              type="button"
              className={classes}
              disabled={!inMonth}
              aria-pressed={selectedDay}
              aria-label={format(day, 'PPP', { locale })}
              onClick={() => onSelect(day)}
            >
              {format(day, 'd', { locale })}
            </button>
          )
        })}
      </div>
    </section>
  )
}
