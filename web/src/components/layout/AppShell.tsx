import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { LanguageSwitcher } from '../common/LanguageSwitcher'

interface AppShellProps {
  children: ReactNode
}

export function AppShell({ children }: AppShellProps) {
  const { t } = useTranslation()

  return (
    <div className="app-shell">
      <header className="brand-bar">
        <div>
          <h1>
            {t('brand.titlePrefix')} <span>{t('brand.titleAccent')}</span>
          </h1>
          <p>{t('brand.tagline')}</p>
        </div>
        <LanguageSwitcher />
      </header>
      {children}
    </div>
  )
}
