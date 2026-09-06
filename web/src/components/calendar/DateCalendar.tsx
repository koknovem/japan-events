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

interface DateCalendarProps {
  selected: Date
  onSelect: (day: Date) => void
  month: Date
  onMonthChange: (month: Date) => void
  cachedDates: Set<string>
}

const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

export function DateCalendar({
  selected,
  onSelect,
  month,
  onMonthChange,
  cachedDates,
}: DateCalendarProps) {
  const monthStart = startOfMonth(month)
  const days = eachDayOfInterval({
    start: startOfWeek(monthStart),
    end: endOfWeek(endOfMonth(monthStart)),
  })

  return (
    <section className="panel panel-calendar" aria-label="Event date calendar">
      <div className="calendar-nav">
        <button
          type="button"
          className="btn btn-ghost"
          aria-label="Previous month"
          onClick={() => onMonthChange(subMonths(month, 1))}
        >
          ‹
        </button>
        <h3>{format(month, 'MMMM yyyy')}</h3>
        <button
          type="button"
          className="btn btn-ghost"
          aria-label="Next month"
          onClick={() => onMonthChange(addMonths(month, 1))}
        >
          ›
        </button>
      </div>

      <div className="calendar-weekdays" aria-hidden>
        {WEEKDAYS.map((d) => (
          <span key={d}>{d}</span>
        ))}
      </div>

      <div className="calendar-grid" role="grid" aria-label={format(month, 'MMMM yyyy')}>
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
              aria-label={format(day, 'MMMM d, yyyy')}
              onClick={() => onSelect(day)}
            >
              {format(day, 'd')}
            </button>
          )
        })}
      </div>
    </section>
  )
}
