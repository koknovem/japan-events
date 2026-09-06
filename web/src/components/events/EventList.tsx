import type { EventItem } from '../../types/events'
import { EventCard } from './EventCard'
import { EmptyState } from '../common/EmptyState'
import { LoadingState } from '../common/LoadingState'

interface EventListProps {
  events: EventItem[]
  loading: boolean
  scraping?: boolean
  emptyMessage: string
  dateLabel: string
}

export function EventList({
  events,
  loading,
  scraping,
  emptyMessage,
  dateLabel,
}: EventListProps) {
  if (loading) {
    return (
      <LoadingState
        label={
          scraping
            ? `Scraping prefecture calendars for ${dateLabel}… this can take several minutes.`
            : `Loading events for ${dateLabel}…`
        }
      />
    )
  }

  if (events.length === 0) {
    return <EmptyState title="No events for this date" message={emptyMessage} />
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
