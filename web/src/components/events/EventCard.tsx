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

function httpUrl(raw: string | null | undefined): string | null {
  if (!raw) return null
  try {
    const url = new URL(raw.trim())
    if (url.protocol !== 'http:' && url.protocol !== 'https:') return null
    url.hash = ''
    return url.toString()
  } catch {
    return null
  }
}

function sourceLink(event: EventItem): { href: string; label: string } | null {
  const href = httpUrl(event.source) ?? httpUrl(event.url)
  if (!href) return null
  try {
    const url = new URL(href)
    const host = url.hostname.replace(/^www\./, '')
    const path = url.pathname === '/' ? '' : url.pathname.replace(/\/$/, '')
    return { href, label: path ? `${host}${path}` : host }
  } catch {
    return { href, label: href }
  }
}

export function EventCard({ event, index }: EventCardProps) {
  const { t } = useTranslation()
  const [imgFailed, setImgFailed] = useState(false)
  const prefLabel = event.site_id
    ? t(`prefectures.${event.site_id}`, { defaultValue: event.prefecture })
    : event.prefecture
  const showImage = Boolean(event.image_url) && !imgFailed
  const source = sourceLink(event)
  const detailHref = httpUrl(event.url)

  const main = (
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

  return (
    <article
      className="event-card"
      style={{ animationDelay: `${Math.min(index, 16) * 0.03}s` }}
    >
      {detailHref ? (
        <a className="event-card-main" href={detailHref} target="_blank" rel="noreferrer">
          {main}
        </a>
      ) : (
        <div className="event-card-main">{main}</div>
      )}
      {source ? (
        <a
          className="event-card-source"
          href={source.href}
          target="_blank"
          rel="noreferrer"
          title={source.href}
          aria-label={`${t('events.source')}: ${source.label}`}
        >
          {source.label}
        </a>
      ) : null}
    </article>
  )
}
