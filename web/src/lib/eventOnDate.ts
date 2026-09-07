import type { EventItem } from '../types/events'

/** True when the event's date range includes YYYY-MM-DD. ISO dates compare lexicographically. */
export function eventOnDate(event: Pick<EventItem, 'start_date' | 'end_date'>, dateKey: string): boolean {
  const start = event.start_date
  const end = event.end_date
  if (!start && !end) return false
  let from = start ?? end!
  let to = end ?? start!
  if (to < from) {
    const swap = from
    from = to
    to = swap
  }
  return from <= dateKey && dateKey <= to
}

export function eventsOnDate<T extends Pick<EventItem, 'start_date' | 'end_date'>>(
  events: T[],
  dateKey: string,
): T[] {
  return events.filter((event) => eventOnDate(event, dateKey))
}
