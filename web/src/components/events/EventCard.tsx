import { useState } from 'react'
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
  const [imgFailed, setImgFailed] = useState(false)
  const prefLabel = event.site_id
    ? t(`prefectures.${event.site_id}`, { defaultValue: event.prefecture })
    : event.prefecture
  const showImage = Boolean(event.image_url) && !imgFailed
  const body = (
    <>
      <div className={`event-card-media${showImage ? '' : ' is-placeholder'}`}>
        {showImage ? (
          <img
            src={event.image_url!}
            alt=""
            loading="lazy"
            decoding="async"
            onError={() => setImgFailed(true)}
          />
        ) : (
          <div className="event-card-placeholder" aria-hidden>
            <span>{prefLabel.slice(0, 1)}</span>
          </div>
        )}
        <span className="event-card-pref">{prefLabel}</span>
      </div>
      <div className="event-card-body">
        <h3>{event.title}</h3>
        <div className="meta">
          <span>{formatRange(event.start_date, event.end_date, t('events.dateTbd'))}</span>
          {event.venue ? <span>{event.venue}</span> : null}
          {event.area ? <span>{event.area}</span> : null}
        </div>
      </div>
    </>
  )

  if (event.url) {
    return (
      <a
        className="event-card event-card-link"
        href={event.url}
        target="_blank"
        rel="noreferrer"
        style={{ animationDelay: `${Math.min(index, 16) * 0.03}s` }}
      >
        {body}
      </a>
    )
  }

  return (
    <article
      className="event-card"
      style={{ animationDelay: `${Math.min(index, 16) * 0.03}s` }}
    >
      {body}
    </article>
  )
}
