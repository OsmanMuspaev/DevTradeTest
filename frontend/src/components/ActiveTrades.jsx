import { useState, useEffect, startTransition } from 'react'
import './ActiveTrades.css'

export default function ActiveTrades() {
  const [trades, setTrades] = useState([])
  const [isLoading, setIsLoading] = useState(false)

  // TODO: Получать реальные сделки с бэкенда
  useEffect(() => {
    // Заглушка — потом заменим на реальный API
    startTransition(() => {
      setIsLoading(true)
    })
    
    const timer = setTimeout(() => {
      startTransition(() => {
        setTrades([
          {
            id: '1',
            symbol: 'BTCUSDT',
            side: 'long',
            entryPrice: 65000,
            currentPrice: 66200,
            pnl: 1.85,
            entryTime: new Date().toISOString(),
            strategyName: 'EMA Cross',
          },
          {
            id: '2',
            symbol: 'ETHUSDT',
            side: 'short',
            entryPrice: 3200,
            currentPrice: 3150,
            pnl: 1.56,
            entryTime: new Date().toISOString(),
            strategyName: 'RSI Divergence',
          },
        ])
        setIsLoading(false)
      })
    }, 500)

    return () => clearTimeout(timer)
  }, [])

  const handleCloseTrade = (id) => {
    // TODO: Отправить запрос на закрытие сделки
    startTransition(() => {
      setTrades(prev => prev.filter(t => t.id !== id))
    })
  }

  if (isLoading) {
    return <div className="active-trades__loading">Загрузка сделок...</div>
  }

  if (trades.length === 0) {
    return (
      <div className="active-trades__empty">
        📭 Нет активных сделок
        <div className="active-trades__hint">
          Запустите стратегию, чтобы она открывала сделки
        </div>
      </div>
    )
  }

  return (
    <div className="active-trades">
      {trades.map(trade => (
        <div key={trade.id} className={`active-trades__item active-trades__item--${trade.side}`}>
          <div className="active-trades__header">
            <span className="active-trades__symbol">{trade.symbol}</span>
            <span className={`active-trades__side active-trades__side--${trade.side}`}>
              {trade.side === 'long' ? '📈 LONG' : '📉 SHORT'}
            </span>
            <button 
              className="active-trades__close"
              onClick={() => handleCloseTrade(trade.id)}
              title="Закрыть сделку"
            >
              ✕
            </button>
          </div>
          
          <div className="active-trades__body">
            <div className="active-trades__row">
              <span className="active-trades__label">Цена входа</span>
              <span className="active-trades__value">${trade.entryPrice.toLocaleString()}</span>
            </div>
            <div className="active-trades__row">
              <span className="active-trades__label">Текущая</span>
              <span className="active-trades__value">${trade.currentPrice.toLocaleString()}</span>
            </div>
            <div className="active-trades__row">
              <span className="active-trades__label">PNL</span>
              <span className={`active-trades__pnl ${trade.pnl >= 0 ? 'active-trades__pnl--positive' : 'active-trades__pnl--negative'}`}>
                {trade.pnl >= 0 ? '+' : ''}{trade.pnl}%
              </span>
            </div>
            <div className="active-trades__row">
              <span className="active-trades__label">Стратегия</span>
              <span className="active-trades__value active-trades__strategy">{trade.strategyName}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}