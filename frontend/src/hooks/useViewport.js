import { useState, useCallback, useMemo, useEffect, startTransition } from 'react'
import { normalizeViewport } from '../utils/candles'

const VIEWPORT_MIN = 30
const VIEWPORT_MAX = 2500

export function useViewport({ totalCandles, maxCount, initialCount = 288, resetKey }) {
  const [viewport, setViewport] = useState({
    start: 0,
    count: initialCount,
  })

  useEffect(() => {
    startTransition(() => {
      setViewport({ start: 0, count: initialCount })
    })
  }, [resetKey, initialCount])

  const normalizedView = useMemo(
    () => normalizeViewport(viewport, totalCandles, VIEWPORT_MIN, maxCount),
    [viewport, totalCandles, maxCount]
  )

  const goLatest = useCallback(() => {
    if (!totalCandles) return
    startTransition(() => {
      setViewport((v) => ({
        ...v,
        start: Math.max(0, totalCandles - v.count),
      }))
    })
  }, [totalCandles])

  const zoomBy = useCallback(
    (factor) => {
      if (!totalCandles) return

      const current = normalizeViewport(viewport, totalCandles, VIEWPORT_MIN, maxCount)
      const center = current.start + current.count / 2
      const nextCount = Math.round(current.count * factor)
      const normalized = normalizeViewport(
        { start: current.start, count: nextCount },
        totalCandles,
        VIEWPORT_MIN,
        maxCount
      )
      const nextStart = Math.round(center - normalized.count / 2)

      startTransition(() => {
        setViewport(
          normalizeViewport(
            { start: nextStart, count: normalized.count },
            totalCandles,
            VIEWPORT_MIN,
            maxCount
          )
        )
      })
    },
    [totalCandles, maxCount, viewport]
  )

  const isAtLatest = useMemo(() => {
    if (!totalCandles) return true
    return normalizedView.start + normalizedView.count >= totalCandles - 5
  }, [normalizedView, totalCandles])

  return {
    viewport: normalizedView,
    setViewport,
    goLatest,
    zoomBy,
    isAtLatest,
    VIEWPORT_MIN,
    VIEWPORT_MAX,
  }
}