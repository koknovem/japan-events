import { useTranslation } from 'react-i18next'
import { setAppLanguage, type AppLang } from '../../i18n'

const OPTIONS: { code: AppLang; labelKey: string }[] = [
  { code: 'en', labelKey: 'language.en' },
  { code: 'zh-TW', labelKey: 'language.zhTW' },
  { code: 'ja', labelKey: 'language.ja' },
]

export function LanguageSwitcher() {
  const { t, i18n } = useTranslation()
  const current = (i18n.language || 'en') as AppLang

  return (
    <div className="lang-switcher" role="group" aria-label={t('language.label')}>
      {OPTIONS.map((opt) => (
        <button
          key={opt.code}
          type="button"
          className={`lang-btn${current === opt.code || current.startsWith(opt.code) ? ' is-active' : ''}`}
          onClick={() => setAppLanguage(opt.code)}
          aria-pressed={current === opt.code}
        >
          {t(opt.labelKey)}
        </button>
      ))}
    </div>
  )
}
