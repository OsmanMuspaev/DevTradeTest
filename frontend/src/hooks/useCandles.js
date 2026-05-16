import { useState, useEffect, useCallback, useRef, useMemo, startTransition } from 'react'
import { fetchCandles } from '../services/candles'
import { mergePages } from '../utils/candles'

const PAGE_SIZE = 200

export function useCandles({ symbol, tf, config }) {
  const [pages, setPages] = useState({})
  const [loadingOlder, setLoadingOlder] = useState(false)
  const [hasMoreOlder, setHasMoreOlder] = useState(true)
  const [connectionStatus, setConnectionStatus] = useState('loading')
  const [connectionError, setConnectionError] = useState(null)
  const [refreshNonce, setRefreshNonce] = useState(0)
  const [state, setState] = useState({
    status: 'ready',
    updatedAt: null,
    resolvedSymbol: null,
    resolvedTimeframe: null,
  })

  const pagesRef = useRef(pages)
  const candles = useMemo(() => mergePages(pages), [pages])
  const candlesRef = useRef(candles)
  const abortControllerRef = useRef(null)
  const isFirstLoadRef = useRef(true)
  const prevSymbolRef = useRef(symbol)
  const prevTfRef = useRef(tf)

  useEffect(() => {
    pagesRef.current = pages
    candlesRef.current = candles
  }, [candles, pages])

  const maxCount = useMemo(() => {
    if (!config?.candles_amount || !tf) return 2500
    const limit = config.candles_amount[tf] ?? 2500
    return Math.min(limit, 2500)
  }, [tf, config])

  const requestRefresh = useCallback(() => {
    if (!symbol || !tf) return
    setRefreshNonce((n) => n + 1)
  }, [symbol, tf])

  const loadOlder = useCallback(async () => {
    if (loadingOlder || !hasMoreOlder || !symbol || !tf) return
    if (!candlesRef.current.length) return

    const offsets = Object.keys(pagesRef.current)
      .map((k) => Number(k))
      .filter((n) => Number.isFinite(n))
    const oldest = offsets.length ? Math.max(...offsets) : 0
    const nextOffset = oldest + PAGE_SIZE

    setLoadingOlder(true)

    try {
      const res = await fetchCandles({ symbol, tf, offset: nextOffset })
      
      if (!res.candles.length) {
        setHasMoreOlder(false)
        return
      }

      setPages((prev) => ({ ...prev, [nextOffset]: res.candles }))
      
      if (connectionStatus === 'error') {
        setConnectionStatus('ready')
        setConnectionError(null)
      }
    } catch (err) {
      console.error('Failed to load older:', err)
    } finally {
      setLoadingOlder(false)
    }
  }, [symbol, tf, loadingOlder, hasMoreOlder, connectionStatus])

  useEffect(() => {
    if (prevSymbolRef.current !== symbol || prevTfRef.current !== tf) {
      prevSymbolRef.current = symbol
      prevTfRef.current = tf
      
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
      
      startTransition(() => {
        setPages({})
        setHasMoreOlder(true)
        setLoadingOlder(false)
        setConnectionStatus('loading')
        setConnectionError(null)
        setState({
          status: 'loading',
          updatedAt: null,
          resolvedSymbol: null,
          resolvedTimeframe: null,
        })
      })
      
      isFirstLoadRef.current = true
    }
  }, [symbol, tf])

  useEffect(() => {
    if (!symbol || !tf) return

    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    
    const controller = new AbortController()
    abortControllerRef.current = controller

    const isFirstLoad = isFirstLoadRef.current
    if (isFirstLoad) {
      isFirstLoadRef.current = false
    }

    fetchCandles({ symbol, tf, offset: 0, signal: controller.signal })
      .then((res) => {
        if (controller.signal.aborted) return
        
        if (isFirstLoad) {
          startTransition(() => {
            setPages({ 0: res.candles })
            setConnectionStatus('ready')
            setConnectionError(null)
            setState({
              status: 'ready',
              updatedAt: Date.now(),
              resolvedSymbol: res.symbol,
              resolvedTimeframe: res.timeFrame,
            })
          })
        } else {
          startTransition(() => {
            setPages(prev => {
              const currentCandles = mergePages(prev)
              const existingTimes = new Set(currentCandles.map(c => c.time))
              const newCandles = res.candles.filter(c => !existingTimes.has(c.time))
              
              if (newCandles.length === 0) return prev
              
              const updatedCandles = [...currentCandles]
              for (const newCandle of newCandles) {
                const lastCandle = updatedCandles[updatedCandles.length - 1]
                if (lastCandle && lastCandle.time === newCandle.time) {
                  updatedCandles[updatedCandles.length - 1] = newCandle
                } else {
                  updatedCandles.push(newCandle)
                }
              }
              
              const newPages = {}
              for (let i = 0; i < updatedCandles.length; i += PAGE_SIZE) {
                newPages[i] = updatedCandles.slice(i, i + PAGE_SIZE)
              }
              return newPages
            })
            
            setConnectionStatus('ready')
            setConnectionError(null)
            setState(s => ({
              ...s,
              status: 'ready',
              updatedAt: Date.now(),
            }))
          })
        }
      })
      .catch((err) => {
        if (controller.signal.aborted) return
        console.error('Failed to fetch candles:', err)
        startTransition(() => {
          setConnectionStatus('error')
          setConnectionError(err?.message || String(err))
          setState(s => ({ ...s, status: 'ready' }))
        })
      })

    return () => {
      controller.abort()
    }
  }, [refreshNonce, symbol, tf])

  return {
    candles,
    maxCount,
    loadingOlder,
    hasMoreOlder,
    connectionStatus,
    connectionError,
    requestRefresh,
    loadOlder,
    state,
  }
}