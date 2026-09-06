import type { ScrapeJob } from '../../types/events'

interface ScrapeControlsProps {
  onScrape: () => void
  busy: boolean
  job: ScrapeJob | null
  hasCache: boolean
}

export function ScrapeControls({ onScrape, busy, job, hasCache }: ScrapeControlsProps) {
  return (
    <div>
      <button type="button" className="btn btn-primary" onClick={onScrape} disabled={busy}>
        {busy ? 'Scraping…' : hasCache ? 'Refresh scrape' : 'Scrape this date'}
      </button>
      {job ? (
        <div className="job-banner" data-status={job.status}>
          Job {job.status}
          {job.status === 'completed'
            ? ` · ${job.event_count} events from ${job.ok_count}/${job.site_count} sites`
            : null}
          {job.error ? ` · ${job.error}` : null}
        </div>
      ) : null}
    </div>
  )
}
