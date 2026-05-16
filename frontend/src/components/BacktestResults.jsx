import './BacktestResults.css'

export default function BacktestResults({ results, isLoading, error }) {
  if (isLoading) {
    return <div className="backtest-results__loading">⏳ Запуск бэктеста...</div>
  }

  if (error) {
    return (
      <div className="backtest-results__error">
        <div>❌ Ошибка</div>
        <div style={{ fontSize: 11, marginTop: 8 }}>{error}</div>
      </div>
    )
  }

  if (!results) {
    return (
      <div className="backtest-results__empty">
        📊 Нажмите «Тест» чтобы запустить бэктест
      </div>
    )
  }

  const isProfit = (results.net_profit || 0) > 0

  return (
    <div className="backtest-results">
      <div className="backtest-results__header">
        <div className="backtest-results__title">
          {results.symbol} · {results.timeframe}
        </div>
        <div className="backtest-results__subtitle">
          Бэктест завершён
        </div>
      </div>

      <div className="backtest-results__stats">
        <div className="backtest-results__stat">
          <div className="backtest-results__stat-label">Чистая прибыль</div>
          <div className={`backtest-results__stat-value ${isProfit ? 'backtest-results__stat-value--positive' : 'backtest-results__stat-value--negative'}`}>
            ${results.net_profit?.toFixed(2)} ({results.net_profit_percent}%)
          </div>
        </div>
        <div className="backtest-results__stat">
          <div className="backtest-results__stat-label">Баланс</div>
          <div className="backtest-results__stat-value">
            ${results.final_balance?.toFixed(2)}
          </div>
        </div>
        <div className="backtest-results__stat">
          <div className="backtest-results__stat-label">Всего сделок</div>
          <div className="backtest-results__stat-value">
            {results.total_trades}
          </div>
        </div>
        <div className="backtest-results__stat">
          <div className="backtest-results__stat-label">Winrate</div>
          <div className="backtest-results__stat-value">
            {results.winrate_percent}%
          </div>
        </div>
        <div className="backtest-results__stat">
          <div className="backtest-results__stat-label">Profit Factor</div>
          <div className="backtest-results__stat-value">
            {results.profit_factor}
          </div>
        </div>
        <div className="backtest-results__stat">
          <div className="backtest-results__stat-label">Max Drawdown</div>
          <div className={`backtest-results__stat-value backtest-results__stat-value--negative`}>
            {results.max_drawdown_percent}%
          </div>
        </div>
      </div>

      {results.trades?.length > 0 && (
        <div className="backtest-results__section">
          <div className="backtest-results__section-title">Последние сделки</div>
          <div style={{ fontSize: 11, color: 'var(--text-dim)', maxHeight: 150, overflowY: 'auto' }}>
            {results.trades.slice(-10).reverse().map((t, i) => (
              <div key={i} style={{ 
                padding: '6px 0', 
                borderBottom: '1px solid var(--border)',
                display: 'flex',
                justifyContent: 'space-between'
              }}>
                <span style={{ color: t.side === 'long' ? '#22c55e' : '#ef4444' }}>
                  {t.side === 'long' ? '📈' : '📉'} {t.side}
                </span>
                <span>${t.pnl_usdt?.toFixed(2)}</span>
                <span style={{ color: t.pnl_percent > 0 ? '#22c55e' : '#ef4444' }}>
                  {t.pnl_percent > 0 ? '+' : ''}{t.pnl_percent?.toFixed(2)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}