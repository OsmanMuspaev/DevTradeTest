import { useState, useEffect, startTransition } from 'react'
import { loadStrategiesFromCache, deleteStrategyFromCache } from '../services/strategiesCache'
import './StrategiesList.css'

export default function StrategiesList({ onSelectStrategy, onNewStrategy, selectedId }) {
  const [strategies, setStrategies] = useState([])

  useEffect(() => {
    startTransition(() => {
      setStrategies(loadStrategiesFromCache())
    })
  }, [])

  const handleDelete = (id, e) => {
    e.stopPropagation()
    if (confirm('Удалить стратегию?')) {
      const updated = deleteStrategyFromCache(id)
      startTransition(() => setStrategies(updated))
      if (selectedId === id && onSelectStrategy) {
        onSelectStrategy(null)
      }
    }
  }

  const formatDate = (dateStr) => {
    try {
      const date = new Date(dateStr)
      return date.toLocaleDateString(undefined, { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
    } catch {
      return ''
    }
  }

  return (
    <div className="strategies-list">
      <button className="strategies-list__new" onClick={onNewStrategy}>
        + Новая стратегия
      </button>

      {strategies.length === 0 ? (
        <div className="strategies-list__empty">
          📭 Нет сохранённых стратегий
        </div>
      ) : (
        strategies.map(s => (
          <div
            key={s.id}
            className={`strategies-list__item ${selectedId === s.id ? 'strategies-list__item--active' : ''}`}
            onClick={() => onSelectStrategy?.(s)}
          >
            <div className="strategies-list__info">
              <div className="strategies-list__title">
                {s.title || 'Без названия'}
              </div>
              <div className="strategies-list__meta">
                <span>{s.language || 'python'}</span>
                <span>·</span>
                <span>{formatDate(s.savedAt)}</span>
              </div>
            </div>
            <div className="strategies-list__actions">
              <button
                className="strategies-list__btn strategies-list__btn--delete"
                onClick={(e) => handleDelete(s.id, e)}
                title="Удалить"
              >
                🗑️
              </button>
            </div>
          </div>
        ))
      )}
    </div>
  )
}