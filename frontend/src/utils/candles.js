export function clamp(n, min, max) {
  return Math.min(max, Math.max(min, n))
}

export function mergePages(pages) {
  const offsets = Object.keys(pages)
    .map((k) => Number(k))
    .filter((n) => Number.isFinite(n))
    .sort((a, b) => a - b)

  const seen = new Set()
  const merged = []

  for (const offset of offsets) {
    const page = pages[offset]
    if (!Array.isArray(page)) continue

    for (const c of page) {
      if (!c || typeof c.time !== 'number') continue
      if (seen.has(c.time)) continue
      seen.add(c.time)
      merged.push(c)
    }
  }

  merged.sort((a, b) => a.time - b.time)
  return merged
}

export function normalizeViewport(viewport, total, minCount, maxCount) {
  const safeTotal = Math.max(0, total)
  if (!safeTotal) return { start: 0, count: 0 }

  const min = Math.max(1, Math.min(minCount, safeTotal))
  const max = Math.max(min, Math.min(maxCount, safeTotal))

  const targetCount = Number.isFinite(viewport?.count)
    ? Math.round(viewport.count)
    : 288
  const count = clamp(targetCount, min, max)

  const maxStart = Math.max(0, safeTotal - count)
  const targetStart = Number.isFinite(viewport?.start) ? viewport.start : maxStart
  const start = clamp(targetStart, 0, maxStart)

  return { start, count }
}