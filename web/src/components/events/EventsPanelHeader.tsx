import { format } from 'date-fns'
import { useTranslation } from 'react-i18next'
import type { EventsResponse } from '../../types/events'
import { dateFnsLocales, type AppLang } from '../../i18n'

interface EventsPanelHeaderProps {
  date: Date
  data: EventsResponse | null
  error: string | null
  scraping?: boolean
}

export function EventsPanelHeader({ date, data, error, scraping }: EventsPanelHeaderProps) {
  const { t, i18n } = useTranslation()
  const lang = (i18n.language as AppLang) in dateFnsLocales ? (i18n.language as AppLang) : 'en'
  const locale = dateFnsLocales[lang]

  return (
    <div className="panel-toolbar">
      <div>
        <h2>{format(date, 'EEEE, MMM d', { locale })}</h2>
        <div style={{ display: 'flex', gap: '0.45rem', flexWrap: 'wrap', marginTop: '0.45rem' }}>
          {scraping ? (
            <span className="meta-chip">
              <strong>{t('events.scrapingChip')}</strong>
            </span>
          ) : data?.cached || data?.scraped ? (
            <span className="meta-chip">
              <strong>{t('events.eventsCount', { count: data.event_count })}</strong>
              {' · '}
              {t('events.sitesCount', { ok: data.ok_count, total: data.site_count })}
              {' · '}
              {data.scraped ? t('events.justScraped') : t('events.cached')}
            </span>
          ) : (
            <span className="meta-chip">{t('events.waiting')}</span>
          )}
          {error ? (
            <span className="meta-chip" style={{ color: 'var(--danger)' }}>
              {error}
            </span>
          ) : null}
        </div>
      </div>
    </div>
  )
}
