import { format } from 'date-fns'
import type { EventsResponse } from '../../types/events'

interface EventsPanelHeaderProps {
  date: Date
  data: EventsResponse | null
  error: string | null
}

export function EventsPanelHeader({ date, data, error }: EventsPanelHeaderProps) {
  return (
    <div className="panel-toolbar">
      <div>
        <h2>{format(date, 'EEEE, MMM d')}</h2>
        <div style={{ display: 'flex', gap: '0.45rem', flexWrap: 'wrap', marginTop: '0.45rem' }}>
          {data?.cached ? (
            <span className="meta-chip">
              <strong>{data.event_count}</strong> events · <strong>{data.ok_count}</strong>/
              {data.site_count} sites
            </span>
          ) : (
            <span className="meta-chip">Not cached yet</span>
          )}
          {error ? <span className="meta-chip" style={{ color: 'var(--danger)' }}>{error}</span> : null}
        </div>
      </div>
    </div>
  )
}
