import CandlestickChart from './CandlestickChart'

export default function ChartSection({
  candles,
  viewport,
  onViewportChange,
  connectionStatus,
  connectionError,
  loadOlder,
  hasMoreOlder,
  loadingOlder,
  state,
  symbol,
  tf,
  maxCount,
  VIEWPORT_MIN,
}) {
  return (
    <section className="card">
      <div className="card__header">
        <div>
          <div className="card__title">
            {state.resolvedSymbol || symbol}{' '}
            <span className="muted">· {tf?.toUpperCase() || ''}</span>
          </div>
          <div className="card__subtitle">
            {connectionStatus === 'loading'
              ? 'Загружаю свечи…'
              : connectionStatus === 'error'
              ? 'Ошибка подключения к серверу'
              : `📊 ${viewport.count} свечей`}
          </div>
        </div>

        <div className="pills">
          <span
            className={`pill pill--${
              connectionStatus === 'error'
                ? 'danger'
                : connectionStatus === 'ready'
                ? 'ok'
                : 'warn'
            }`}
          >
            {connectionStatus === 'ready'
              ? 'online'
              : connectionStatus === 'error'
              ? 'offline'
              : 'loading'}
          </span>
          {state.updatedAt && (
            <span className="pill mono">
              {new Date(state.updatedAt).toLocaleTimeString(undefined, {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
              })}
            </span>
          )}
        </div>
      </div>

      <CandlestickChart
        candles={candles}
        viewportStart={viewport.start}
        viewportCount={viewport.count}
        minCount={VIEWPORT_MIN}
        maxCount={maxCount}
        onViewportChange={onViewportChange}
        onRequestOlder={loadOlder}
        loadingOlder={loadingOlder}
        hasMoreOlder={hasMoreOlder}
      />

      {connectionError && (
        <div className="error">
          <div className="error__title">Не удалось получить свечи</div>
          <div className="error__body mono">{connectionError}</div>
          <div className="error__hint">
            Подними бэк: <span className="mono">docker compose up -d</span>
          </div>
        </div>
      )}
    </section>
  )
}