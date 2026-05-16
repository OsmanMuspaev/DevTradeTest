import { useState, useEffect, useRef } from 'react'

const LIVE_INTERVAL_MS = Math.max(
  1000,
  Number(import.meta.env.LIVE_INTERVAL_MS ?? 1000) || 1000
)

export function useLiveUpdates({ onRefresh, isAtLatest, candlesLength, onGoLatest }) {
  const [live, setLive] = useState(true)
  const isAtLatestRef = useRef(isAtLatest)
  const candlesLengthRef = useRef(candlesLength)

  useEffect(() => {
    isAtLatestRef.current = isAtLatest
    candlesLengthRef.current = candlesLength
  }, [isAtLatest, candlesLength])

  useEffect(() => {
    if (!live) return

    const interval = setInterval(() => {
      if (isAtLatestRef.current && candlesLengthRef.current > 0) {
        onRefresh()
      }
    }, LIVE_INTERVAL_MS)

    return () => clearInterval(interval)
  }, [live, onRefresh])

  useEffect(() => {
    if (!live) return
    if (!candlesLength) return
    
    if (isAtLatestRef.current) {
      setTimeout(() => {
        onGoLatest()
      }, 50)
    }
  }, [candlesLength, live, onGoLatest])

  const liveStatus = !live ? 'off' : isAtLatest ? 'on' : 'paused'

  return { live, setLive, liveStatus }
}