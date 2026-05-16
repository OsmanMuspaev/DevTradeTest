const DEFAULT_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

function toCandle(row) {
  return {
    time: Number(row.open_time),
    open: Number(row.open_price),
    high: Number(row.high_price),
    low: Number(row.low_price),
    close: Number(row.close_price),
    volume: Number(row.volume),
    isGrow: Boolean(row.is_grow),
  }
}

export async function fetchCandles({ symbol, tf, offset = 0, signal } = {}) {
  if (!symbol) throw new Error('symbol is required')
  if (!tf) throw new Error('tf is required')

  const url = new URL(
    `${DEFAULT_BASE_URL}/api/core/coin/${encodeURIComponent(symbol)}`,
    window.location.origin,
  )
  url.searchParams.set('tf', tf)
  url.searchParams.set('offset', String(offset))

  const res = await fetch(url.toString(), { signal, cache: 'no-store' })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `HTTP ${res.status}`)
  }

  const json = await res.json()
  const data = Array.isArray(json?.data) ? json.data : []

  const candles = data.map(toCandle).sort((a, b) => a.time - b.time)

  return {
    symbol: json?.symbol ?? symbol,
    timeFrame: json?.time_frame ?? tf,
    candles,
  }
}
