export default function Topbar({
  symbol,
  tf,
  config,
  onSymbolChange,
  onTfChange,
  onRefresh,
  onZoomIn,
  onZoomOut,
  onLiveToggle,
  isAtLatest,
  liveStatus,
  onGoLatest,
}) {
  const timeframes = config?.timeframes?.map((tf) => {
    if (typeof tf === 'string') return { key: tf, label: tf.toUpperCase() }
    return { key: tf.key, label: tf.label || tf.key.toUpperCase() }
  }) || []

  const tfIndex = timeframes.findIndex((t) => t.key === tf)

  return (
    <header className="topbar">
      <div className="brand">
        <div className="brand__name">DevTrade</div>
      </div>

      <div className="controls">
        <label className="field">
          <span className="field__label">Монета</span>
          <select
            className="select"
            value={symbol || ''}
            onChange={(e) => onSymbolChange(e.target.value)}
          >
            {config?.crypto_list?.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>

        {timeframes.length > 0 && (
          <div
            className="segmented"
            role="group"
            aria-label="Таймфрейм"
            style={{ '--seg-index': tfIndex, '--seg-count': timeframes.length }}
          >
            {timeframes.map((t) => (
              <button
                key={t.key}
                type="button"
                className={`segmented__btn${t.key === tf ? ' segmented__btn--active' : ''}`}
                onClick={() => {
                  if (t.key !== tf) onTfChange(t.key)
                }}
              >
                {t.label}
              </button>
            ))}
          </div>
        )}

        <button type="button" className="refresh" onClick={onRefresh} title="Обновить сейчас">
          ↻
        </button>

        <button type="button" className="refresh" onClick={onZoomOut} title="Zoom out">
          −
        </button>

        <button type="button" className="refresh" onClick={onZoomIn} title="Zoom in">
          +
        </button>

        <button
          type="button"
          className={`live live--${liveStatus}`}
          onClick={onLiveToggle}
          title={
            !isAtLatest
              ? 'Live ставится на паузу, если ты смотришь историю'
              : `Авто-обновление каждые ${Math.round(Number(import.meta.env.LIVE_INTERVAL_MS ?? 1000) / 1000)}с`
          }
        >
          Live <span className="mono">{liveStatus}</span>
        </button>

        {!isAtLatest && (
          <button type="button" className="refresh" onClick={onGoLatest} title="Вернуться к текущему">
            ⇢
          </button>
        )}
      </div>
    </header>
  )
}