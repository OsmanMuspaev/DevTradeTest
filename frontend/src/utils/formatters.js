export function formatCompactNumber(value) {
  return new Intl.NumberFormat(undefined, { notation: 'compact' }).format(value)
}

export function formatTime(seconds) {
  return new Date(seconds * 1000).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}