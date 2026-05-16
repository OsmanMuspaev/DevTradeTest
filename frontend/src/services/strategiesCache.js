const STORAGE_KEY = 'devtrade_strategies'

export function loadStrategiesFromCache() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const strategies = JSON.parse(raw)
    return strategies.map(s => ({
      ...s,
      savedAt: new Date(s.savedAt),
    }))
  } catch {
    return []
  }
}

export function saveStrategyToCache(strategy) {
  const strategies = loadStrategiesFromCache()
  const existingIndex = strategies.findIndex(s => s.id === strategy.id)
  
  const newStrategy = {
    ...strategy,
    id: strategy.id || crypto.randomUUID(),
    savedAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  }
  
  if (existingIndex >= 0) {
    strategies[existingIndex] = newStrategy
  } else {
    strategies.unshift(newStrategy)
  }
  
  // Ограничиваем до 50 стратегий
  const trimmed = strategies.slice(0, 50)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed))
  return trimmed
}

export function deleteStrategyFromCache(id) {
  const strategies = loadStrategiesFromCache()
  const filtered = strategies.filter(s => s.id !== id)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered))
  return filtered
}

export function updateStrategyInCache(id, updates) {
  const strategies = loadStrategiesFromCache()
  const index = strategies.findIndex(s => s.id === id)
  if (index >= 0) {
    strategies[index] = { ...strategies[index], ...updates, updatedAt: new Date().toISOString() }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(strategies))
  }
  return strategies
}