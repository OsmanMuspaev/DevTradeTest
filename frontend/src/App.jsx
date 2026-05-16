import { useState, useCallback, useMemo } from 'react'
import { useAuth } from './components/useAuth'
import { useConfig } from './hooks/useConfig'
import { useCandles } from './hooks/useCandles'
import { useViewport } from './hooks/useViewport'
import { useLiveUpdates } from './hooks/useLiveUpdates'
import Topbar from './components/Topbar'
import ChartSection from './components/ChartSection'
import SidePanel from './components/SidePanel'
import './App.css'

export default function App() {
  const { isAuthenticated } = useAuth()
  const { config, loading: configLoading, error: configError } = useConfig()

  const [symbol, setSymbol] = useState(null)
  const [tf, setTf] = useState(null)

  const { candles, maxCount, loadingOlder, hasMoreOlder, connectionStatus, connectionError, requestRefresh, loadOlder, state } =
    useCandles({ symbol, tf, config })

  const { viewport, setViewport, goLatest, zoomBy, isAtLatest, VIEWPORT_MIN } = useViewport({
    totalCandles: candles.length,
    maxCount,
    initialCount: 288,
    resetKey: `${symbol}-${tf}`,
  })

  const { live, setLive, liveStatus } = useLiveUpdates({
    onRefresh: requestRefresh,
    isAtLatest,
    candlesLength: candles.length,
    onGoLatest: goLatest,
  })

  const handleSymbolChange = useCallback((newSymbol) => {
    setSymbol(newSymbol)
  }, [])

  const handleTimeframeChange = useCallback((newTf) => {
    setTf(newTf)
  }, [])

  const lastCandle = useMemo(() => {
    if (!candles.length || !viewport.count) return null
    const lastIndex = Math.min(
      Math.floor(viewport.start + viewport.count - 1),
      candles.length - 1
    )
    return lastIndex >= 0 ? candles[lastIndex] : null
  }, [candles, viewport])

  if (configLoading) {
    return <div className="app"><div className="loading-screen">Загрузка конфигурации...</div></div>
  }

  if (configError) {
    return (
      <div className="app">
        <div className="error-screen">
          <h2>Ошибка загрузки params.json</h2>
          <p>{configError}</p>
        </div>
      </div>
    )
  }

  if (config && !symbol && config.crypto_list?.length) {
    setSymbol(config.crypto_list[0])
  }
  if (config && !tf && config.timeframes?.length) {
    const firstTf = config.timeframes[0]
    setTf(typeof firstTf === 'string' ? firstTf : firstTf.key)
  }

  return (
    <div className="app">
      <Topbar
        symbol={symbol}
        tf={tf}
        config={config}
        onSymbolChange={handleSymbolChange}
        onTfChange={handleTimeframeChange}
        onRefresh={requestRefresh}
        onZoomIn={() => zoomBy(0.85)}
        onZoomOut={() => zoomBy(1.18)}
        onLiveToggle={() => setLive(!live)}
        isAtLatest={isAtLatest}
        liveStatus={liveStatus}
        onGoLatest={goLatest}
      />

      <main className="content">
        <div className="grid">
          <ChartSection
            candles={candles}
            viewport={viewport}
            onViewportChange={setViewport}
            connectionStatus={connectionStatus}
            connectionError={connectionError}
            loadOlder={loadOlder}
            hasMoreOlder={hasMoreOlder}
            loadingOlder={loadingOlder}
            state={state}
            symbol={symbol}
            tf={tf}
            maxCount={maxCount}
            VIEWPORT_MIN={VIEWPORT_MIN}
          />

          <SidePanel 
            isAuthenticated={isAuthenticated} 
            lastCandle={lastCandle} 
            symbol={symbol}
            timeframe={tf}       
          />
        </div>
      </main>
    </div>
  )
}