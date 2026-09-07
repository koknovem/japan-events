import { format, formatDistanceToNow, parseISO } from 'date-fns'
import { useTranslation } from 'react-i18next'
import type { EventsResponse, LoadProgress } from '../../types/events'
import { dateFnsLocales, type AppLang } from '../../i18n'

interface EventsPanelHeaderProps {
  date: Date
  data: EventsResponse | null
  error: string | null
  loading?: boolean
  scraping?: boolean
  refreshing?: boolean
  progress?: LoadProgress | null
}

export function EventsPanelHeader({ date, data, error, loading, scraping, refreshing, progress }: EventsPanelHeaderProps) {
  const { t, i18n } = useTranslation()
  const lang = (i18n.language as AppLang) in dateFnsLocales ? (i18n.language as AppLang) : 'en'
  const locale = dateFnsLocales[lang]
  const scrapeProgress = scraping && progress?.mode === 'scrape' ? progress : null
  const downloadProgress = loading && progress?.mode === 'download' ? progress : null
  const refreshProgress = refreshing && !scraping ? progress : null
  const cacheLabel = data?.generated_at
    ? formatDistanceToNow(parseISO(data.generated_at), { addSuffix: true, locale })
    : t('events.cached')

  return (
    <div className="panel-toolbar">
      <div>
        <h2>{format(date, 'EEEE, MMM d', { locale })}</h2>
        <div style={{ display: 'flex', gap: '0.45rem', flexWrap: 'wrap', marginTop: '0.45rem' }}>
          {scrapeProgress ? (
            <span className="meta-chip">
              <strong>
                {scrapeProgress.queued || scrapeProgress.phase === 'queued'
                  ? t('events.queuedChip')
                  : scrapeProgress.total > 0
                    ? t('events.progressSites', { done: scrapeProgress.done, total: scrapeProgress.total })
                    : t('events.scrapingChip')}
              </strong>
              {scrapeProgress.percent != null ? ` · ${scrapeProgress.percent}%` : null}
              {data && data.event_count > 0 ? ` · ${t('events.eventsCount', { count: data.event_count })}` : null}
            </span>
          ) : scraping ? (
            <span className="meta-chip">
              <strong>{t('events.scrapingChip')}</strong>
            </span>
          ) : downloadProgress ? (
            <span className="meta-chip">
              <strong>
                {downloadProgress.percent != null
                  ? t('events.progressDownload', { percent: downloadProgress.percent })
                  : t('events.loadingShort')}
              </strong>
            </span>
          ) : data?.cached || data?.scraped ? (
            <span className="meta-chip">
              <strong>{t('events.eventsCount', { count: data.event_count })}</strong>
              {' · '}
              {t('events.sitesCount', { ok: data.ok_count, total: data.site_count })}
              {' · '}
              {data.scraped ? t('events.justScraped') : cacheLabel}
            </span>
          ) : (
            <span className="meta-chip">{t('events.waiting')}</span>
          )}
          {refreshProgress ? (
            <span className="meta-chip">
              <strong>
                {refreshProgress.phase === 'scanning'
                  ? t('events.checkingUpdates', {
                      done: refreshProgress.done,
                      total: refreshProgress.total,
                    })
                  : t('events.updatingChanged', {
                      done: refreshProgress.done,
                      total: refreshProgress.total,
                    })}
              </strong>
              {refreshProgress.percent != null ? ` · ${refreshProgress.percent}%` : null}
            </span>
          ) : null}
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
