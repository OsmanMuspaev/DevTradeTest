import { useMemo } from 'react'
import { formatTime, formatCompactNumber } from '../utils/formatters'

export default function SummaryBlock({ lastCandle }) {
  const summary = useMemo(() => {
    if (!lastCandle) return null
    const delta = lastCandle.close - lastCandle.open
    const pct = lastCandle.open ? (delta / lastCandle.open) * 100 : 0
    return {
      time: formatTime(lastCandle.time),
      open: lastCandle.open,
      high: lastCandle.high,
      low: lastCandle.low,
      close: lastCandle.close,
      volume: lastCandle.volume,
      delta,
      pct,
      direction: delta >= 0 ? 'up' : 'down',
    }
  }, [lastCandle])

  if (!summary) {
    return <div className="empty muted">Пока нет данных — жду свечи…</div>
  }

  return (
    <>
      <div className={`stat stat--${summary.direction}`}>
        <div className="stat__label">Изменение</div>
        <div className="stat__value mono">
          {summary.delta >= 0 ? '+' : ''}
          {summary.delta.toFixed(2)}{' '}
          <span className="muted">
            ({summary.pct >= 0 ? '+' : ''}
            {summary.pct.toFixed(2)}%)
          </span>
        </div>
      </div>

      <div className="kv">
        <div className="kv__k">Time</div>
        <div className="kv__v mono">{summary.time}</div>
        <div className="kv__k">Open</div>
        <div className="kv__v mono">{summary.open.toFixed(2)}</div>
        <div className="kv__k">High</div>
        <div className="kv__v mono">{summary.high.toFixed(2)}</div>
        <div className="kv__k">Low</div>
        <div className="kv__v mono">{summary.low.toFixed(2)}</div>
        <div className="kv__k">Close</div>
        <div className="kv__v mono">{summary.close.toFixed(2)}</div>
        <div className="kv__k">Volume</div>
        <div className="kv__v mono">{formatCompactNumber(summary.volume)}</div>
      </div>
    </>
  )
}