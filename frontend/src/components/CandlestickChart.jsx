import { useEffect, useMemo, useRef, useState } from 'react'
import './CandlestickChart.css'

const PAD = { l: 70, r: 24, t: 16, b: 34 }
const DEFAULT_MIN_COUNT = 30
const DEFAULT_MAX_COUNT = 320

function clamp(n, min, max) {
  return Math.min(max, Math.max(min, n))
}

function formatPrice(value) {
  const abs = Math.abs(value)
  const maximumFractionDigits =
    abs >= 1000 ? 2 : abs >= 100 ? 2 : abs >= 10 ? 3 : abs >= 1 ? 4 : 6

  return new Intl.NumberFormat(undefined, {
    maximumFractionDigits,
  }).format(value)
}

function formatTime(seconds) {
  const d = new Date(seconds * 1000)
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function getTheme(el) {
  const styles = getComputedStyle(el)
  return {
    bg: styles.getPropertyValue('--chart-bg').trim() || '#0b1220',
    grid: styles.getPropertyValue('--chart-grid').trim() || 'rgba(148,163,184,0.14)',
    text: styles.getPropertyValue('--chart-text').trim() || '#cbd5e1',
    sans:
      styles.getPropertyValue('--sans').trim() ||
      "system-ui, -apple-system, 'Segoe UI', Roboto, Inter, sans-serif",
    mono:
      styles.getPropertyValue('--mono').trim() ||
      'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
    up: styles.getPropertyValue('--candle-up').trim() || '#22c55e',
    down: styles.getPropertyValue('--candle-down').trim() || '#ef4444',
    crosshair:
      styles.getPropertyValue('--chart-crosshair').trim() || 'rgba(167,139,250,0.55)',
  }
}

function quantile(sorted, q) {
  const n = sorted.length
  if (!n) return NaN
  const pos = (n - 1) * q
  const base = Math.floor(pos)
  const rest = pos - base
  const v0 = sorted[base]
  const v1 = sorted[base + 1]
  if (!Number.isFinite(v0)) return NaN
  if (!Number.isFinite(v1)) return v0
  return v0 + rest * (v1 - v0)
}

function getAutoRange(candles) {
  if (!candles || !candles.length) return null
  
  const lows = []
  const highs = []

  for (const c of candles) {
    if (!c) continue
    const low = Number(c.low)
    const high = Number(c.high)
    if (Number.isFinite(low)) lows.push(low)
    if (Number.isFinite(high)) highs.push(high)
  }

  if (!lows.length || !highs.length) return null

  lows.sort((a, b) => a - b)
  highs.sort((a, b) => a - b)

  const fullMin = lows[0]
  const fullMax = highs[highs.length - 1]

  if (!Number.isFinite(fullMin) || !Number.isFinite(fullMax)) return null
  if (fullMin === fullMax) return { min: fullMin - 1, max: fullMax + 1 }

  const qLow = quantile(lows, 0.02)
  const qHigh = quantile(highs, 0.98)

  const trimmedMin = Number.isFinite(qLow) ? qLow : fullMin
  const trimmedMax = Number.isFinite(qHigh) ? qHigh : fullMax

  const fullRange = fullMax - fullMin
  const trimmedRange = trimmedMax - trimmedMin

  const useTrimmed =
    trimmedRange > 0 && fullRange / trimmedRange >= 3.5 && trimmedMax > trimmedMin

  return {
    min: useTrimmed ? trimmedMin : fullMin,
    max: useTrimmed ? trimmedMax : fullMax,
  }
}

function normalizeViewport({ start, count }, total, minCount, maxCount) {
  const safeTotal = Math.max(0, total)
  if (!safeTotal) return { start: 0, count: 0 }

  const min = Math.max(1, Math.min(minCount, safeTotal))
  const max = Math.max(min, Math.min(maxCount, safeTotal))

  let c = Number.isFinite(count) ? Math.round(count) : min
  c = clamp(c, min, max)

  const maxStart = Math.max(0, safeTotal - c)
  let s = Number.isFinite(start) ? Math.round(start) : 0
  s = clamp(s, 0, maxStart)

  return { start: s, count: c }
}

function drawChart({ canvas, container, candles, hover, width, height }) {
  if (!canvas || !container) return
  if (!width || !height) return

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const dpr = window.devicePixelRatio || 1
  const w = Math.max(1, Math.floor(width * dpr))
  const h = Math.max(1, Math.floor(height * dpr))

  if (canvas.width !== w) canvas.width = w
  if (canvas.height !== h) canvas.height = h
  if (canvas.style.width !== `${width}px`) canvas.style.width = `${width}px`
  if (canvas.style.height !== `${height}px`) canvas.style.height = `${height}px`

  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.clearRect(0, 0, width, height)

  const theme = getTheme(container)

  const plotW = width - PAD.l - PAD.r
  const plotH = height - PAD.t - PAD.b
  if (plotW <= 10 || plotH <= 10) return

  ctx.fillStyle = theme.bg
  ctx.fillRect(0, 0, width, height)

  const count = candles.length
  if (!count) {
    ctx.fillStyle = theme.text
    ctx.font = `500 14px ${theme.sans}`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText('Нет данных по свечам', width / 2, height / 2)
    return
  }

  const baseRange = getAutoRange(candles)
  if (!baseRange) return

  let max = baseRange.max
  let min = baseRange.min

  const range = max - min
  if (!Number.isFinite(range) || range <= 0) return

  max += range * 0.08
  min -= range * 0.08

  const yFor = (price) => PAD.t + ((max - price) / (max - min)) * plotH
  const yClamp = (y) => clamp(y, PAD.t, PAD.t + plotH)
  const step = plotW / count
  const xFor = (i) => PAD.l + i * step + step / 2

  // Рисуем сетку
  const gridLines = 5
  ctx.strokeStyle = theme.grid
  ctx.lineWidth = 1
  ctx.beginPath()
  for (let i = 0; i < gridLines; i++) {
    const y = PAD.t + (i * plotH) / (gridLines - 1)
    ctx.moveTo(PAD.l, y)
    ctx.lineTo(width - PAD.r, y)
  }
  ctx.stroke()

  const timeLabelCount = 4
  ctx.beginPath()
  for (let i = 0; i < timeLabelCount; i++) {
    const idx = Math.round((i * (count - 1)) / (timeLabelCount - 1))
    const x = xFor(idx)
    ctx.moveTo(x, PAD.t)
    ctx.lineTo(x, PAD.t + plotH)
  }
  ctx.stroke()

  // Цены на сетке
  ctx.fillStyle = theme.text
  ctx.font = `12px ${theme.mono}`
  ctx.textAlign = 'left'
  ctx.textBaseline = 'middle'
  for (let i = 0; i < gridLines; i++) {
    const y = PAD.t + (i * plotH) / (gridLines - 1)
    const price = max - (i * (max - min)) / (gridLines - 1)
    ctx.fillText(formatPrice(price), 10, y)
  }

  const bodyW = clamp(step * 0.78, 3, 24)
  const wickW = clamp(step * 0.14, 1, 2.4)

  // Рисуем свечи
  for (let i = 0; i < candles.length; i++) {
    const c = candles[i]
    const isUp = c.close >= c.open
    const color = isUp ? theme.up : theme.down
    const x = xFor(i)

    const yHigh = yClamp(yFor(c.high))
    const yLow = yClamp(yFor(c.low))
    const yOpen = yClamp(yFor(c.open))
    const yClose = yClamp(yFor(c.close))

    ctx.strokeStyle = color
    ctx.lineWidth = wickW
    ctx.beginPath()
    ctx.moveTo(x, yHigh)
    ctx.lineTo(x, yLow)
    ctx.stroke()

    const top = Math.min(yOpen, yClose)
    const bottom = Math.max(yOpen, yClose)
    const bodyH = Math.max(1, bottom - top)
    ctx.fillStyle = color
    ctx.fillRect(x - bodyW / 2, top, bodyW, bodyH)
  }

  const bottomY = height - 12
  ctx.fillStyle = theme.text
  ctx.font = `12px ${theme.mono}`
  ctx.textBaseline = 'alphabetic'

  for (let i = 0; i < timeLabelCount; i++) {
    const idx = Math.round((i * (count - 1)) / (timeLabelCount - 1))
    let x = xFor(idx)
    const d = new Date(candles[idx].time * 1000)
    const label = d.toLocaleDateString(undefined, {
      month: 'short',
      day: '2-digit',
      year: 'numeric',
    })
    
    if (i === timeLabelCount - 1) {
      ctx.textAlign = 'right'
      x = Math.min(x, width - PAD.r - 4)
    } else if (i === 0) {
      ctx.textAlign = 'left'
    } else {
      ctx.textAlign = 'center'
    }
    
    ctx.fillText(label, x, bottomY)
  }

  ctx.textAlign = 'center'

  if (hover && hover.index >= 0 && hover.index < count) {
    const x = xFor(hover.index)
    const y = clamp(hover.y, PAD.t, PAD.t + plotH)

    ctx.strokeStyle = theme.crosshair
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.moveTo(x, PAD.t)
    ctx.lineTo(x, PAD.t + plotH)
    ctx.moveTo(PAD.l, y)
    ctx.lineTo(width - PAD.r, y)
    ctx.stroke()
  }
}

export default function CandlestickChart({
  candles,
  height = 520,
  viewportStart = 0,
  viewportCount = 120,
  minCount = DEFAULT_MIN_COUNT,
  maxCount = DEFAULT_MAX_COUNT,
  onViewportChange,
  onRequestOlder,
  loadingOlder = false,
  hasMoreOlder = true,
}) {
  const containerRef = useRef(null)
  const canvasRef = useRef(null)
  const [size, setSize] = useState({ width: 0, height: 0 })
  const [hover, setHover] = useState(null)
  const [dragging, setDragging] = useState(false)

  const all = useMemo(() => (Array.isArray(candles) ? candles : []), [candles])
  const total = all.length

  const viewport = useMemo(
    () => normalizeViewport({ start: viewportStart, count: viewportCount }, total, minCount, maxCount),
    [maxCount, minCount, total, viewportCount, viewportStart],
  )

  const visible = useMemo(() => {
    if (!viewport.count) return []
    const start = Math.min(viewport.start, total - 1)
    const end = Math.min(start + viewport.count, total)
    return all.slice(start, end)
  }, [all, viewport.count, viewport.start, total])

  const apiRef = useRef({
    total,
    viewport,
    minCount,
    maxCount,
    onViewportChange,
    onRequestOlder,
    loadingOlder,
    hasMoreOlder,
  })
  
  useEffect(() => {
    apiRef.current = {
      total,
      viewport,
      minCount,
      maxCount,
      onViewportChange,
      onRequestOlder,
      loadingOlder,
      hasMoreOlder,
    }
  }, [
    hasMoreOlder,
    loadingOlder,
    maxCount,
    minCount,
    onRequestOlder,
    onViewportChange,
    total,
    viewport,
  ])

  const wheelRef = useRef({ pan: 0, zoom: 0 })
  const dragRef = useRef(null)
  const rafRef = useRef(0)
  const pendingViewportRef = useRef(null)

  const emitViewport = (nextViewport) => {
    const api = apiRef.current
    if (typeof api.onViewportChange !== 'function') return

    pendingViewportRef.current = nextViewport
    if (rafRef.current) return
    rafRef.current = window.requestAnimationFrame(() => {
      rafRef.current = 0
      const next = pendingViewportRef.current
      pendingViewportRef.current = null
      if (!next) return
      api.onViewportChange(next)
    })
  }

  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    const ro = new ResizeObserver(([entry]) => {
      const cr = entry.contentRect
      setSize({ width: Math.floor(cr.width), height: Math.floor(cr.height) })
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  useEffect(() => {
    drawChart({
      canvas: canvasRef.current,
      container: containerRef.current,
      candles: visible,
      hover,
      width: size.width,
      height: size.height,
    })
  }, [visible, hover, size.height, size.width])

  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    const onWheel = (e) => {
      const api = apiRef.current
      if (!api.total || !size.width || !size.height) return

      e.preventDefault()

      const width = size.width
      const plotW = width - PAD.l - PAD.r
      if (plotW <= 10) return

      const rect = el.getBoundingClientRect()
      const x = e.clientX - rect.left
      const plotX = clamp(x - PAD.l, 0, plotW)
      const ratio = plotW ? plotX / plotW : 0

      const current = api.viewport
      const stepPx = plotW / Math.max(1, current.count)

      if (e.ctrlKey) {
        const direction = Math.sign(e.deltaY || 0)
        if (!direction) return

        const factor = direction > 0 ? 1.12 : 0.89
        wheelRef.current.zoom = 0

        const anchor = clamp(
          current.start + Math.round(ratio * Math.max(0, current.count - 1)),
          0,
          api.total - 1,
        )

        const targetCountRaw = Math.round(current.count * factor)
        const targetViewport = normalizeViewport(
          {
            start: anchor - Math.round(ratio * Math.max(0, targetCountRaw - 1)),
            count: targetCountRaw,
          },
          api.total,
          api.minCount,
          api.maxCount,
        )

        emitViewport(targetViewport)
        return
      }

      const useX = Math.abs(e.deltaX) > Math.abs(e.deltaY)
      const delta = useX ? e.deltaX : e.deltaY
      const sign = useX ? 1 : -1
      wheelRef.current.pan += (sign * delta) / stepPx

      const shift = Math.trunc(wheelRef.current.pan)
      if (!shift) return
      wheelRef.current.pan -= shift

      let nextStart = current.start + shift
      if (nextStart < 0) {
        nextStart = 0
        if (api.hasMoreOlder && typeof api.onRequestOlder === 'function' && !api.loadingOlder) {
          api.onRequestOlder()
        }
      }

      const maxStart = Math.max(0, api.total - current.count)
      nextStart = clamp(nextStart, 0, maxStart)
      emitViewport({ start: nextStart, count: current.count })
    }

    el.addEventListener('wheel', onWheel, { passive: false })
    return () => el.removeEventListener('wheel', onWheel)
  }, [size.height, size.width])

  const onMove = (e) => {
    const el = containerRef.current
    if (!el || !visible.length || !size.width) return
    if (dragging) return

    const rect = el.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top

    const plotW = size.width - PAD.l - PAD.r
    if (plotW <= 10) return
    const step = plotW / visible.length
    const plotX = x - PAD.l
    if (plotX < 0 || plotX > plotW) {
      setHover(null)
      return
    }

    const index = clamp(Math.floor(plotX / step), 0, visible.length - 1)
    setHover((prev) => {
      if (
        prev &&
        prev.index === index &&
        Math.abs(prev.x - x) < 0.5 &&
        Math.abs(prev.y - y) < 0.5
      ) {
        return prev
      }
      return { index, x, y, candle: visible[index] }
    })
  }

  const onLeave = () => setHover(null)

  const onPointerDown = (e) => {
    const el = containerRef.current
    const api = apiRef.current
    if (!el || !api.total || e.button !== 0) return

    e.preventDefault()
    el.setPointerCapture(e.pointerId)
    setDragging(true)
    setHover(null)

    dragRef.current = {
      pointerId: e.pointerId,
      startX: e.clientX,
      startStart: api.viewport.start,
      startCount: api.viewport.count,
    }
  }

  const onPointerMove = (e) => {
    if (!dragRef.current) return
    const el = containerRef.current
    const api = apiRef.current
    if (!el || !api.total) return

    const width = size.width
    const plotW = width - PAD.l - PAD.r
    if (plotW <= 10) return

    const stepPx = plotW / Math.max(1, dragRef.current.startCount)
    const dx = e.clientX - dragRef.current.startX
    const delta = Math.round(dx / stepPx)

    let nextStart = dragRef.current.startStart + delta
    if (nextStart < 0) {
      nextStart = 0
      if (api.hasMoreOlder && typeof api.onRequestOlder === 'function' && !api.loadingOlder) {
        api.onRequestOlder()
      }
    }

    const maxStart = Math.max(0, api.total - dragRef.current.startCount)
    nextStart = clamp(nextStart, 0, maxStart)
    emitViewport({ start: nextStart, count: dragRef.current.startCount })
  }

  const onPointerUp = (e) => {
    const el = containerRef.current
    if (el && dragRef.current?.pointerId === e.pointerId) {
      try {
        el.releasePointerCapture(e.pointerId)
      } catch {
        // ignore
      }
    }

    dragRef.current = null
    setDragging(false)
  }

  const onDoubleClick = () => {
    const api = apiRef.current
    if (!api.total) return
    const start = Math.max(0, api.total - api.viewport.count)
    emitViewport({ start, count: api.viewport.count })
  }

  const tooltip = useMemo(() => {
    if (!hover?.candle) return null

    const c = hover.candle
    const delta = c.close - c.open
    const pct = c.open ? (delta / c.open) * 100 : 0
    const direction = delta >= 0 ? 'up' : 'down'

    const tooltipW = 240
    const tooltipH = 128
    let left = hover.x + 14
    let top = hover.y + 14
    if (left + tooltipW > size.width) left = hover.x - tooltipW - 14
    if (top + tooltipH > size.height) top = hover.y - tooltipH - 14
    left = clamp(left, 10, Math.max(10, size.width - tooltipW - 10))
    top = clamp(top, 10, Math.max(10, size.height - tooltipH - 10))

    return {
      left,
      top,
      direction,
      time: formatTime(c.time),
      open: formatPrice(c.open),
      high: formatPrice(c.high),
      low: formatPrice(c.low),
      close: formatPrice(c.close),
      change: `${delta >= 0 ? '+' : ''}${formatPrice(delta)} (${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%)`,
    }
  }, [hover, size.height, size.width])

  return (
    <div
      ref={containerRef}
      className={`candles-chart${dragging ? ' candles-chart--dragging' : ''}`}
      style={{ height }}
      onMouseMove={onMove}
      onMouseLeave={onLeave}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
      onDoubleClick={onDoubleClick}
    >
      <canvas ref={canvasRef} className="candles-canvas" />
      {tooltip ? (
        <div
          className={`candles-tooltip candles-tooltip--${tooltip.direction}`}
          style={{ left: tooltip.left, top: tooltip.top }}
        >
          <div className="candles-tooltip__time">{tooltip.time}</div>
          <div className="candles-tooltip__grid">
            <div>O</div>
            <div>{tooltip.open}</div>
            <div>H</div>
            <div>{tooltip.high}</div>
            <div>L</div>
            <div>{tooltip.low}</div>
            <div>C</div>
            <div>{tooltip.close}</div>
          </div>
          <div className="candles-tooltip__change">{tooltip.change}</div>
        </div>
      ) : null}
    </div>
  )
}