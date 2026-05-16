import { useCallback, useMemo, useRef, useState, useEffect, startTransition } from 'react'
import { testStrategy } from '../services/strategies'
import { saveStrategyToCache } from '../services/strategiesCache'
import BacktestResults from './BacktestResults'
import './StrategyEditor.css'

const DEFAULT_CODE = `# DevTrade Strategy (template)

def strategy(open, high, low, close, volume, time):
    # Параметры
    fast_length = 9
    slow_length = 21
    
    # Расчёт EMA
    ema_fast = ta.ema(close, fast_length)
    ema_slow = ta.ema(close, slow_length)
    
    # Сигналы
    long_entry = crossover(ema_fast, ema_slow)
    long_exit = crossunder(ema_fast, ema_slow)
    short_entry = crossunder(ema_fast, ema_slow)
    short_exit = crossover(ema_fast, ema_slow)
    
    return {
        "long_entry": long_entry,
        "long_exit": long_exit,
        "short_entry": short_entry,
        "short_exit": short_exit,
    }
`

function insertAtSelection(value, selectionStart, selectionEnd, insert) {
  return value.slice(0, selectionStart) + insert + value.slice(selectionEnd)
}

export default function StrategyEditor({ initialStrategy, onSave, symbol, timeframe, onRunStrategy }) {
  const [title, setTitle] = useState(initialStrategy?.title || '')
  const [language, setLanguage] = useState(initialStrategy?.language || 'python')
  const [code, setCode] = useState(initialStrategy?.code || DEFAULT_CODE)
  const [backtestResults, setBacktestResults] = useState(null)
  const [isBacktesting, setIsBacktesting] = useState(false)
  const [backtestError, setBacktestError] = useState(null)
  const [isRunning, setIsRunning] = useState(false)
  const textareaRef = useRef(null)
  const saveTimeoutRef = useRef(null)

  // Автосохранение
  useEffect(() => {
    if (!title.trim() && code === DEFAULT_CODE) return
    
    if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current)
    
    saveTimeoutRef.current = setTimeout(() => {
      const strategy = {
        id: initialStrategy?.id,
        title: title.trim() || 'Untitled',
        language,
        code,
        savedAt: new Date().toISOString(),
      }
      saveStrategyToCache(strategy)
      onSave?.(strategy)
    }, 1000)

    return () => {
      if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current)
    }
  }, [title, language, code, initialStrategy?.id, onSave])

  useEffect(() => {
    if (initialStrategy) {
      startTransition(() => {
        setTitle(initialStrategy.title || '')
        setLanguage(initialStrategy.language || 'python')
        setCode(initialStrategy.code || DEFAULT_CODE)
      })
    }
  }, [initialStrategy])

  const canTest = useMemo(() => {
    return !!(symbol && timeframe && code.trim().length > 0 && !isBacktesting)
  }, [code, isBacktesting, symbol, timeframe])

  const onRunBacktest = useCallback(async () => {
    if (!symbol || !timeframe) {
      setBacktestError('Выберите монету и таймфрейм на верхней панели')
      return
    }
    
    setIsBacktesting(true)
    setBacktestError(null)
    setBacktestResults(null)
    
    try {
      const res = await testStrategy({
        symbol,
        timeframe,
        script: code,
        initialBalance: 10000,
      })
      startTransition(() => setBacktestResults(res))
    } catch (err) {
      startTransition(() => setBacktestError(err?.message || String(err)))
    } finally {
      startTransition(() => setIsBacktesting(false))
    }
  }, [code, symbol, timeframe])

  const handleRunStrategy = useCallback(() => {
    setIsRunning(true)
    // Запускаем стратегию через родительский компонент
    onRunStrategy?.({
      id: initialStrategy?.id || crypto.randomUUID(),
      name: title.trim() || 'Untitled',
      code,
      symbol,
      timeframe,
    })
  }, [initialStrategy, title, code, symbol, timeframe, onRunStrategy])

  const onKeyDown = useCallback((e) => {
    if (e.key === 'Tab') {
      e.preventDefault()
      const el = textareaRef.current
      if (!el) return
      const start = el.selectionStart ?? 0
      const end = el.selectionEnd ?? 0
      const tab = '  '
      const next = insertAtSelection(el.value, start, end, tab)
      setCode(next)
      requestAnimationFrame(() => {
        el.selectionStart = el.selectionEnd = start + tab.length
      })
    }

    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault()
      onRunBacktest()
    }
  }, [onRunBacktest])

  if (!symbol || !timeframe) {
    return (
      <div className="strategy__warning">
        ⚠️ Выберите монету и таймфрейм на верхней панели
      </div>
    )
  }

  return (
    <div className="strategy">
      <div className="strategy__header">
        <div className="strategy__header-title">
          {initialStrategy ? 'Редактирование стратегии' : 'Новая стратегия'}
        </div>
      </div>
      <div className="strategy__row">
        <label className="strategy__field">
          <span className="strategy__label">Название</span>
          <input
            className="strategy__input"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Напр. EMA Cross"
          />
        </label>

        <label className="strategy__field">
          <span className="strategy__label">Язык</span>
          <select
            className="strategy__select"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
          >
            <option value="python">python</option>
          </select>
        </label>
      </div>

      <div className="strategy__editor">
        <textarea
          ref={textareaRef}
          className="strategy__textarea"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          onKeyDown={onKeyDown}
          spellCheck={false}
        />
      </div>

      <div className="strategy__actions">
        <button
          type="button"
          className="strategy__btn strategy__btn--backtest"
          onClick={onRunBacktest}
          disabled={!canTest}
        >
          {isBacktesting ? '⏳ Тест...' : '📊 Бэктест'}
        </button>
        
        <button
          type="button"
          className="strategy__btn strategy__btn--run"
          onClick={handleRunStrategy}
          disabled={isRunning}
        >
          {isRunning ? '▶️ Запуск...' : '▶️ Запустить'}
        </button>
      </div>

      {/* Ошибки с ограничением высоты */}
      <div className="strategy__errors">
        {backtestError && (
          <div className="strategy__error mono">
            <div className="strategy__error-title">❌ Ошибка бэктеста</div>
            <div className="strategy__error-text">{backtestError}</div>
          </div>
        )}
      </div>

      <div className="strategy__backtest-results">
        <BacktestResults 
          results={backtestResults}
          isLoading={isBacktesting}
          error={backtestError}
        />
      </div>
    </div>
  )
}