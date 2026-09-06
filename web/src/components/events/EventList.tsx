import type { EventItem } from '../../types/events'
import { EventCard } from './EventCard'
import { EmptyState } from '../common/EmptyState'
import { LoadingState } from '../common/LoadingState'

interface EventListProps {
  events: EventItem[]
  loading: boolean
  emptyMessage: string
  onScrape?: () => void
  scrapeBusy?: boolean
  showScrape?: boolean
}

export function EventList({
  events,
  loading,
  emptyMessage,
  onScrape,
  scrapeBusy,
  showScrape,
}: EventListProps) {
  if (loading) return <LoadingState label="Loading events for this date…" />

  if (events.length === 0) {
    return (
      <EmptyState
        title="No events for this date"
        message={emptyMessage}
        action={
          showScrape && onScrape ? (
            <button type="button" className="btn btn-primary" onClick={onScrape} disabled={scrapeBusy}>
              {scrapeBusy ? 'Scraping…' : 'Scrape this date'}
            </button>
          ) : null
        }
      />
    )
  }

  return (
    <div className="event-list" role="list">
      {events.map((event, index) => (
        <div key={`${event.site_id}-${event.title}-${event.url ?? index}`} role="listitem">
          <EventCard event={event} index={index} />
        </div>
      ))}
    </div>
  )
}
