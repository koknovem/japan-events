import { useTranslation } from 'react-i18next'
import { setAppLanguage, type AppLang } from '../../i18n'

const OPTIONS: { code: AppLang; labelKey: string }[] = [
  { code: 'en', labelKey: 'language.en' },
  { code: 'zh-TW', labelKey: 'language.zhTW' },
  { code: 'zh-CN', labelKey: 'language.zhCN' },
  { code: 'ja', labelKey: 'language.ja' },
]

export function LanguageSwitcher() {
  const { t, i18n } = useTranslation()
  const current = (i18n.language || 'en') as AppLang

  return (
    <div className="lang-switcher" role="group" aria-label={t('language.label')}>
      {OPTIONS.map((opt) => {
        const active = current === opt.code || current.toLowerCase().startsWith(opt.code.toLowerCase())
        return (
          <button
            key={opt.code}
            type="button"
            className={`lang-btn${active ? ' is-active' : ''}`}
            onClick={() => setAppLanguage(opt.code)}
            aria-pressed={active}
          >
            {t(opt.labelKey)}
          </button>
        )
      })}
    </div>
  )
}
