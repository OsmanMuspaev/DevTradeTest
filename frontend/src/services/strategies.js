const GATEWAY_URL = import.meta.env.VITE_GATEWAY_URL || '/api'

export async function submitStrategy({ code }) {
  const response = await fetch(`${GATEWAY_URL}/sandbox/backtest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      symbol: 'BTCUSDT',      // TODO: взять из текущего state
      timeframe: '1h',        // TODO: взять из текущего state
      script: code,
      initial_balance: 10000,
      commission_percent: 0.1,
      slippage_percent: 0.0,
    }),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || error.error || 'Submission failed')
  }

  return await response.json()
}

export async function testStrategy({ symbol, timeframe, script, initialBalance = 10000 }) {
  const response = await fetch(`${GATEWAY_URL}/sandbox/backtest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      symbol,
      timeframe,
      script,
      initial_balance: initialBalance,
      commission_percent: 0.1,
      slippage_percent: 0.0,
    }),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || error.error || 'Backtest failed')
  }

  return await response.json()
}