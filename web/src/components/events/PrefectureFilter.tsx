import type { Site } from '../../types/events'

interface PrefectureFilterProps {
  sites: Site[]
  value: string | null
  onChange: (id: string | null) => void
}

export function PrefectureFilter({ sites, value, onChange }: PrefectureFilterProps) {
  const regions = Array.from(new Set(sites.map((s) => s.region)))

  return (
    <label className="filter-row">
      <span className="meta-chip">Prefecture</span>
      <select
        className="select"
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value || null)}
        aria-label="Filter by prefecture"
      >
        <option value="">All prefectures</option>
        {regions.map((region) => (
          <optgroup key={region} label={region}>
            {sites
              .filter((s) => s.region === region)
              .map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                  {s.source_org ? ` · ${s.source_org}` : ''}
                </option>
              ))}
          </optgroup>
        ))}
      </select>
    </label>
  )
}
