import type { ReactNode } from 'react'

interface AppShellProps {
  children: ReactNode
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="app-shell">
      <header className="brand-bar">
        <div>
          <h1>
            Japan <span>Events</span>
          </h1>
          <p>
            Pick a date on the calendar to browse festivals and events scraped from prefectural
            tourism association calendars across Japan.
          </p>
        </div>
      </header>
      {children}
    </div>
  )
}
