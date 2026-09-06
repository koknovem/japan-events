import { useTranslation } from 'react-i18next'
import type { Site } from '../../types/events'

interface PrefectureFilterProps {
  sites: Site[]
  value: string | null
  onChange: (id: string | null) => void
}

export function PrefectureFilter({ sites, value, onChange }: PrefectureFilterProps) {
  const { t } = useTranslation()
  const regions = Array.from(new Set(sites.map((s) => s.region)))

  return (
    <label className="filter-row">
      <span className="meta-chip">{t('filter.prefecture')}</span>
      <select
        className="select"
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value || null)}
        aria-label={t('filter.aria')}
      >
        <option value="">{t('filter.all')}</option>
        {regions.map((region) => (
          <optgroup key={region} label={t(`regions.${region}`, { defaultValue: region })}>
            {sites
              .filter((s) => s.region === region)
              .map((s) => (
                <option key={s.id} value={s.id}>
                  {t(`prefectures.${s.id}`, { defaultValue: s.name })}
                  {s.source_org ? ` · ${s.source_org}` : ''}
                </option>
              ))}
          </optgroup>
        ))}
      </select>
    </label>
  )
}
