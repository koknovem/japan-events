/** Parse a typed calendar date. Accepts YYYY-MM-DD, YYYY-MM, and slash/dot variants. Local calendar dates only. */
export function parseTypedDate(raw: string, fallback: Date = new Date()): Date | null {
  const trimmed = raw
    .trim()
    .replace(/[./]/g, '-')
    .replace(/年/g, '-')
    .replace(/月/g, '-')
    .replace(/日/g, '')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')

  const ymd = trimmed.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/)
  if (ymd) {
    return localDate(Number(ymd[1]), Number(ymd[2]), Number(ymd[3]))
  }

  const ym = trimmed.match(/^(\d{4})-(\d{1,2})$/)
  if (ym) {
    const year = Number(ym[1])
    const month = Number(ym[2])
    const last = new Date(year, month, 0).getDate()
    const day = Math.min(fallback.getDate(), last)
    return localDate(year, month, day)
  }

  return null
}

function localDate(year: number, month: number, day: number): Date | null {
  if (month < 1 || month > 12 || day < 1 || day > 31) return null
  const value = new Date(year, month - 1, day)
  if (
    value.getFullYear() !== year ||
    value.getMonth() !== month - 1 ||
    value.getDate() !== day
  ) {
    return null
  }
  return value
}
