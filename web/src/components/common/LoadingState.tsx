interface LoadingStateProps {
  label?: string
}

export function LoadingState({ label = 'Loading…' }: LoadingStateProps) {
  return (
    <div className="loading-state" role="status" aria-live="polite">
      <div className="dot" />
      <span>{label}</span>
    </div>
  )
}
