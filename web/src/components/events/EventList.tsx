import { useTranslation } from 'react-i18next'
import type { EventItem, LoadProgress } from '../../types/events'
import { EventCard } from './EventCard'
import { EmptyState } from '../common/EmptyState'
import { LoadingState } from '../common/LoadingState'

interface EventListProps {
  events: EventItem[]
  loading: boolean
  scraping?: boolean
  progress?: LoadProgress | null
  emptyMessage: string
  dateLabel: string
}

export function EventList({
  events,
  loading,
  scraping,
  progress,
  emptyMessage,
  dateLabel,
}: EventListProps) {
  const { t } = useTranslation()

  if (loading && events.length === 0) {
    return (
      <LoadingState
        label={
          scraping
            ? t('events.scraping', { date: dateLabel })
            : t('events.loading', { date: dateLabel })
        }
        progress={progress}
      />
    )
  }

  if (events.length === 0) {
    return <EmptyState title={t('events.emptyTitle')} message={emptyMessage} />
  }

  return (
    <div className="event-grid" role="list">
      {events.map((event, index) => (
        <div
          key={`${event.site_id}-${event.lang ?? ''}-${event.title}-${event.url ?? index}`}
          role="listitem"
        >
          <EventCard event={event} index={index} />
        </div>
      ))}
    </div>
  )
}
