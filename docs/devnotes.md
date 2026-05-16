### temp dev note
`git rev-list -n 1 --before="1 month ago" master`  

---

### Тест Docker-изоляции sandbox (полный стек)

Убедись что стек запущен:
```bash
docker compose up -d
```

Затем отправь backtest-запрос через gateway (полная цепочка: nginx → gateway → sandbox → devtrade-runner):
```bash
curl -s -X POST http://localhost/api/sandbox/backtest \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTCUSDT","timeframe":"1h","script":"def strategy(open,high,low,close,volume,time):\n    ema5=ta.ema(close,5)\n    ema10=ta.ema(close,10)\n    return {\"long_entry\":crossover(ema5,ema10),\"long_exit\":crossunder(ema5,ema10)}\n","initial_balance":10000,"commission_percent":0.1,"slippage_percent":0.0}' | python3 -m json.tool
```

Или напрямую в sandbox (минуя gateway/nginx), если нужно тестировать только его:
```bash
curl -s -X POST http://localhost:8010/backtest \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTCUSDT","timeframe":"1h","script":"def strategy(open,high,low,close,volume,time):\n    ema5=ta.ema(close,5)\n    ema10=ta.ema(close,10)\n    return {\"long_entry\":crossover(ema5,ema10),\"long_exit\":crossunder(ema5,ema10)}\n","initial_balance":10000,"commission_percent":0.1,"slippage_percent":0.0}' | python3 -m json.tool
```

Проверить что sandbox реально спавнит runner-контейнер (в отдельном терминале во время запроса):
```bash
watch -n 0.5 docker ps --filter ancestor=devtrade-runner
```

Ожидаемый результат: JSON с `"symbol": "BTCUSDT"`, `"total_trades": ...`, `"equity_curve": [...]`

