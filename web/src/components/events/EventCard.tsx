import { useTranslation } from 'react-i18next'
import type { EventItem } from '../../types/events'

interface EventCardProps {
  event: EventItem
  index: number
}

function formatRange(start: string | null, end: string | null, tbd: string) {
  if (start && end && start !== end) return `${start} → ${end}`
  return start ?? end ?? tbd
}

export function EventCard({ event, index }: EventCardProps) {
  const { t } = useTranslation()
  const prefLabel = event.site_id
    ? t(`prefectures.${event.site_id}`, { defaultValue: event.prefecture })
    : event.prefecture

  return (
    <article
      className="event-card"
      style={{ animationDelay: `${Math.min(index, 12) * 0.04}s` }}
    >
      <div>
        <div className="pref-tag">{prefLabel}</div>
        <h3>{event.title}</h3>
        <div className="meta">
          <span>{formatRange(event.start_date, event.end_date, t('events.dateTbd'))}</span>
          {event.start_time ? (
            <span>
              {event.start_time}
              {event.end_time ? `–${event.end_time}` : ''}
            </span>
          ) : null}
          {event.venue ? <span>{event.venue}</span> : null}
          {event.area ? <span>{event.area}</span> : null}
          {event.category ? <span>{event.category}</span> : null}
        </div>
      </div>
      {event.url ? (
        <a className="detail-link" href={event.url} target="_blank" rel="noreferrer">
          {t('events.open')}
        </a>
      ) : null}
    </article>
  )
}
