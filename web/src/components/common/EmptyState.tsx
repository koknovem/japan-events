import type { ReactNode } from 'react'

interface EmptyStateProps {
  title: string
  message: string
  action?: ReactNode
}

export function EmptyState({ title, message, action }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <strong style={{ color: 'var(--mist)', fontFamily: 'var(--font-display)', fontSize: '1.2rem' }}>
        {title}
      </strong>
      <p style={{ margin: 0, maxWidth: '28rem', lineHeight: 1.5 }}>{message}</p>
      {action}
    </div>
  )
}
