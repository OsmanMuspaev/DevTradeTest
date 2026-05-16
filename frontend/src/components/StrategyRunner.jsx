import { useState, useEffect, startTransition } from 'react'
import './StrategyRunner.css'

export default function StrategyRunner({ strategy, onStop }) {
  const [status, setStatus] = useState('starting')
  const [logs, setLogs] = useState([])
  const [lastSignal, setLastSignal] = useState(null)
  const [error, setError] = useState(null)

  // Симуляция работы стратегии
  useEffect(() => {
    let intervalId = null
    let isMounted = true

    const runStrategy = async () => {
      try {
        startTransition(() => {
          setStatus('running')
        })

        // TODO: Здесь будет реальный WebSocket или polling
        intervalId = setInterval(() => {
          if (!isMounted) return
          
          // Симуляция сигнала
          const sides = ['long', 'short', 'flat']
          const randomSide = sides[Math.floor(Math.random() * sides.length)]
          const hasSignal = Math.random() > 0.7
          
          if (hasSignal && randomSide !== 'flat') {
            const mockSignal = {
              timestamp: new Date().toISOString(),
              side: randomSide,
              confidence: Math.random(),
              price: 65000 + Math.random() * 1000,
            }
            
            startTransition(() => {
              setLastSignal(mockSignal)
              setLogs(prev => [...prev.slice(-49), {
                time: new Date().toLocaleTimeString(),
                msg: `${mockSignal.side.toUpperCase()} сигнал с confidence ${(mockSignal.confidence * 100).toFixed(0)}%`,
                type: mockSignal.side === 'long' ? 'success' : 'warning'
              }])
            })
          }
        }, 5000) // каждые 5 секунд

      } catch (err) {
        startTransition(() => {
          setError(err.message)
          setStatus('error')
        })
      }
    }

    runStrategy()

    return () => {
      isMounted = false
      if (intervalId) {
        clearInterval(intervalId)
      }
    }
  }, [])

  const handleStop = () => {
    setStatus('stopped')
    setLogs(prev => [...prev, {
      time: new Date().toLocaleTimeString(),
      msg: 'Стратегия остановлена пользователем',
      type: 'info'
    }])
    onStop?.()
  }

  const getStatusText = () => {
    switch (status) {
      case 'running': return '🟢 Работает'
      case 'starting': return '🟡 Запуск...'
      case 'stopped': return '⚫ Остановлена'
      case 'error': return '🔴 Ошибка'
      default: return '🟡 Неизвестно'
    }
  }

  const getSignalSideClass = (side) => {
    switch (side) {
      case 'long': return 'strategy-runner__signal-side--long'
      case 'short': return 'strategy-runner__signal-side--short'
      default: return 'strategy-runner__signal-side--flat'
    }
  }

  const getSignalSideText = (side) => {
    switch (side) {
      case 'long': return '📈 LONG'
      case 'short': return '📉 SHORT'
      default: return '⚪ FLAT'
    }
  }

  return (
    <div className="strategy-runner">
      <div className="strategy-runner__header">
        <div className="strategy-runner__info">
          <div className="strategy-runner__name">{strategy?.name || 'Без названия'}</div>
          <div className={`strategy-runner__status strategy-runner__status--${status}`}>
            {getStatusText()}
          </div>
        </div>
        <button 
          className="strategy-runner__stop"
          onClick={handleStop}
          disabled={status === 'stopped'}
        >
          ⏹️ Остановить
        </button>
      </div>

      {strategy?.symbol && strategy?.timeframe && (
        <div className="strategy-runner__pair">
          {strategy.symbol} · {strategy.timeframe}
        </div>
      )}

      {error && (
        <div className="strategy-runner__error">
          <div className="strategy-runner__error-title">❌ Ошибка выполнения</div>
          <div className="strategy-runner__error-text">{error}</div>
        </div>
      )}

      {lastSignal && (
        <div className="strategy-runner__signal">
          <div className="strategy-runner__signal-title">📡 Последний сигнал</div>
          <div className={`strategy-runner__signal-side ${getSignalSideClass(lastSignal.side)}`}>
            {getSignalSideText(lastSignal.side)}
          </div>
          <div className="strategy-runner__signal-price">
            ${lastSignal.price?.toFixed(2)}
          </div>
        </div>
      )}

      <div className="strategy-runner__logs">
        <div className="strategy-runner__logs-title">📋 Логи</div>
        <div className="strategy-runner__logs-list">
          {logs.length === 0 ? (
            <div className="strategy-runner__log-empty">Ожидание сигналов...</div>
          ) : (
            logs.map((log, i) => (
              <div key={i} className={`strategy-runner__log strategy-runner__log--${log.type}`}>
                <span className="strategy-runner__log-time">{log.time}</span>
                <span className="strategy-runner__log-msg">{log.msg}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}