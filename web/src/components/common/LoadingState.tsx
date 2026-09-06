import { useTranslation } from 'react-i18next'
import type { LoadProgress } from '../../types/events'

interface LoadingStateProps {
  label?: string
  progress?: LoadProgress | null
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function LoadingState({ label = 'Loading…', progress }: LoadingStateProps) {
  const { t } = useTranslation()
  const determinate = progress?.percent != null
  const percent = determinate ? Math.max(0, Math.min(100, progress.percent ?? 0)) : 0
  const scrape = progress?.mode === 'scrape'
  const runningNames = (progress?.running ?? []).map((id) => t(`prefectures.${id}`, { defaultValue: id }))

  let detail = label
  if (scrape && progress) {
    if (progress.phase === 'combining') detail = t('events.progressCombining')
    else if (progress.phase === 'starting' || progress.total === 0) detail = t('events.progressStarting')
    else detail = t('events.progressSites', { done: progress.done, total: progress.total })
  } else if (progress?.mode === 'download' && progress.totalBytes) {
    detail = t('events.progressDownloadBytes', {
      loaded: formatBytes(progress.loadedBytes ?? 0),
      total: formatBytes(progress.totalBytes),
    })
  }

  return (
    <div className="loading-state" role="status" aria-live="polite">
      <div className="load-progress-head">
        <div>
          <p className="load-progress-kicker">{label}</p>
          <p className="load-progress-detail">{detail}</p>
        </div>
        <div
          className="load-progress-pct"
          aria-hidden={determinate ? undefined : true}
        >
          {determinate ? `${percent}%` : '—'}
        </div>
      </div>

      <div
        className="load-progress-track"
        role="progressbar"
        aria-label={detail}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={determinate ? percent : undefined}
      >
        <div
          className={`load-progress-fill${determinate ? '' : ' is-indeterminate'}`}
          style={determinate ? { width: `${percent}%` } : undefined}
        />
      </div>

      {scrape && progress && progress.eventsSoFar > 0 ? (
        <p className="load-progress-meta">{t('events.progressEvents', { count: progress.eventsSoFar })}</p>
      ) : null}

      {runningNames.length > 0 ? (
        <p className="load-progress-meta">{t('events.progressCurrent', { names: runningNames.join(' · ') })}</p>
      ) : null}

      {scrape && progress && (progress.concurrency ?? 0) > 0 ? (
        <p className="load-progress-meta">{t('events.progressParallel', { count: progress.concurrency })}</p>
      ) : null}

      {scrape && progress && progress.sites.length > 0 ? (
        <div className="site-ticks" aria-hidden="true">
          {progress.sites.map((site) => (
            <span
              key={site.id}
              className="site-tick"
              data-status={site.status}
              title={`${t(`prefectures.${site.id}`, { defaultValue: site.prefecture })} · ${site.status}${
                site.event_count ? ` · ${site.event_count}` : ''
              }`}
            />
          ))}
        </div>
      ) : null}
    </div>
  )
}
