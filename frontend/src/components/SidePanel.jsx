import { useState, useMemo } from 'react'
import AiChat from './AiChat'
import StrategiesPanel from './StrategiesPanel'
import SummaryBlock from './SummaryBlock'
import ActiveTrades from './ActiveTrades'
import './SidePanel.css'

export default function SidePanel({ isAuthenticated, lastCandle, symbol, timeframe }) {
  const [sideTab, setSideTab] = useState('strategies')
  const [strategiesView, setStrategiesView] = useState('editor') // 'editor', 'saved', 'running'

  const sideTabs = useMemo(
    () => [
      { key: 'trades', label: 'Сделки', locked: !isAuthenticated },
      { key: 'strategies', label: 'Стратегии', locked: !isAuthenticated },
      { key: 'ai', label: 'AI', locked: !isAuthenticated },
      { key: 'summary', label: 'Сводка', locked: false },
    ],
    [isAuthenticated]
  )

  const sideIndex = sideTabs.findIndex((t) => t.key === sideTab)

  const renderContent = () => {
    switch (sideTab) {
      case 'trades':
        return <ActiveTrades />
      case 'strategies':
        return isAuthenticated ? (
          <StrategiesPanel 
            symbol={symbol} 
            timeframe={timeframe}
            view={strategiesView}
            onViewChange={setStrategiesView}
          />
        ) : (
          <div className="empty muted">🔒 Войдите через GitHub</div>
        )
      case 'ai':
        return isAuthenticated ? (
          <AiChat />
        ) : (
          <div className="empty muted">🔒 Войдите через GitHub</div>
        )
      default:
        return <SummaryBlock lastCandle={lastCandle} />
    }
  }

  return (
    <aside className="side">
      <section className="card card--side">
        <div className="card__header">
          <div>
            <div className="card__title">
              {sideTab === 'trades'
                ? 'Сделки'
                : sideTab === 'strategies'
                ? 'Стратегии'
                : sideTab === 'ai'
                ? 'Нейросеть'
                : 'Сводка'}
            </div>
            <div className="card__subtitle">
              {sideTab === 'trades'
                ? 'Активные позиции'
                : sideTab === 'strategies'
                ? 'Редактор и список стратегий'
                : sideTab === 'ai'
                ? 'Помощник по коду'
                : 'Последняя свеча'}
            </div>
          </div>

          <div
            className="segmented segmented--dock"
            role="tablist"
            style={{ '--seg-index': sideIndex, '--seg-count': sideTabs.length }}
          >
            {sideTabs.map((t) => (
              <button
                key={t.key}
                type="button"
                className={`segmented__btn${
                  t.key === sideTab ? ' segmented__btn--active' : ''
                }${t.locked ? ' segmented__btn--locked' : ''}`}
                onClick={() => !t.locked && setSideTab(t.key)}
                disabled={t.locked}
              >
                {t.locked ? '🔒 ' : ''}
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {renderContent()}
      </section>
    </aside>
  )
}