import { useState } from 'react'
import StrategyEditor from './StrategyEditor'
import StrategiesList from './StrategiesList'
import StrategyRunner from './StrategyRunner'
import './StrategiesPanel.css'

export default function StrategiesPanel({ symbol, timeframe, view, onViewChange }) {
  const [selectedStrategy, setSelectedStrategy] = useState(null)
  const [runningStrategies, setRunningStrategies] = useState([])

  // Загрузка сохранённой стратегии при выборе
  const handleSelectStrategy = (strategy) => {
    setSelectedStrategy(strategy)
    onViewChange('editor')
  }

  const handleNewStrategy = () => {
    setSelectedStrategy(null)
    onViewChange('editor')
  }

  const handleBackToSaved = () => {
    onViewChange('saved')
  }

  const handleRunStrategy = (strategy) => {
    setRunningStrategies(prev => [...prev, {
      ...strategy,
      runId: crypto.randomUUID(),
      startedAt: new Date().toISOString(),
      status: 'running'
    }])
    // Переключаемся на вкладку запущенных
    onViewChange('running')
  }

  const handleStopStrategy = (runId) => {
    setRunningStrategies(prev => prev.filter(s => s.runId !== runId))
  }

  return (
    <div className="strategies-panel">
      <div className="strategies-panel__tabs">
        <button
          className={`strategies-panel__tab ${view === 'editor' ? 'strategies-panel__tab--active' : ''}`}
          onClick={() => onViewChange('editor')}
        >
          ✏️ Редактор
        </button>
        <button
          className={`strategies-panel__tab ${view === 'saved' ? 'strategies-panel__tab--active' : ''}`}
          onClick={() => onViewChange('saved')}
        >
          💾 Сохранённые
        </button>
        <button
          className={`strategies-panel__tab ${view === 'running' ? 'strategies-panel__tab--active' : ''}`}
          onClick={() => onViewChange('running')}
        >
          🏃‍♂️ Запущенные {runningStrategies.length > 0 && `(${runningStrategies.length})`}
        </button>
      </div>

      <div className="strategies-panel__content">
        {view === 'editor' && (
          <StrategyEditor
            initialStrategy={selectedStrategy}
            symbol={symbol}
            timeframe={timeframe}
            onRunStrategy={handleRunStrategy}
            onBack={handleBackToSaved}
          />
        )}

        {view === 'saved' && (
          <StrategiesList
            onSelectStrategy={handleSelectStrategy}
            onNewStrategy={handleNewStrategy}
            selectedId={selectedStrategy?.id}
          />
        )}

        {view === 'running' && (
          <div className="running-strategies">
            {runningStrategies.length === 0 ? (
              <div className="empty muted">
                📭 Нет запущенных стратегий
                <div className="running-strategies__hint">
                  Запустите стратегию из редактора или списка сохранённых
                </div>
              </div>
            ) : (
              runningStrategies.map(s => (
                <StrategyRunner
                  key={s.runId}
                  strategy={s}
                  onStop={() => handleStopStrategy(s.runId)}
                />
              ))
            )}
          </div>
        )}
      </div>
    </div>
  )
}