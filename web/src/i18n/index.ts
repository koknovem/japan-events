import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import { enUS, ja, zhCN, zhTW } from 'date-fns/locale'
import type { Locale } from 'date-fns'

import en from './locales/en.json'
import zhTw from './locales/zh-TW.json'
import zhCn from './locales/zh-CN.json'
import jaLocale from './locales/ja.json'

export const SUPPORTED_LANGS = ['en', 'zh-TW', 'zh-CN', 'ja'] as const
export type AppLang = (typeof SUPPORTED_LANGS)[number]

export const dateFnsLocales: Record<AppLang, Locale> = {
  en: enUS,
  'zh-TW': zhTW,
  'zh-CN': zhCN,
  ja,
}

const STORAGE_KEY = 'japan-events-lang'

function detectLang(): AppLang {
  const saved = localStorage.getItem(STORAGE_KEY) as AppLang | null
  if (saved && (SUPPORTED_LANGS as readonly string[]).includes(saved)) return saved

  const nav = navigator.language.toLowerCase()
  if (nav === 'zh-cn' || nav === 'zh-hans' || nav.startsWith('zh-cn')) return 'zh-CN'
  if (nav.startsWith('zh')) return 'zh-TW'
  if (nav.startsWith('ja')) return 'ja'
  return 'en'
}

void i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    'zh-TW': { translation: zhTw },
    'zh-CN': { translation: zhCn },
    ja: { translation: jaLocale },
  },
  lng: detectLang(),
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
})

i18n.on('languageChanged', (lng) => {
  localStorage.setItem(STORAGE_KEY, lng)
  document.documentElement.lang = lng
})

document.documentElement.lang = i18n.language

export function setAppLanguage(lang: AppLang) {
  void i18n.changeLanguage(lang)
}

export default i18n
