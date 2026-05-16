import json
import socket as socket_module

import docker as docker_sdk
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from db import get_candles

app = FastAPI()

RUNNER_IMAGE = "devtrade-runner"
RUNNER_TIMEOUT = 60

try:
    _docker = docker_sdk.from_env()
except Exception:
    _docker = None


class BacktestRequest(BaseModel):
    symbol: str
    timeframe: str
    script: str
    initial_balance: float = 10000
    commission_percent: float = 0.1
    slippage_percent: float = 0.0


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/backtest")
def backtest(payload: BacktestRequest):
    if _docker is None:
        raise HTTPException(status_code=500, detail="Docker socket not available")

    data = get_candles(payload.symbol, payload.timeframe)
    if data is None:
        raise HTTPException(
            status_code=404,
            detail=f"No candles found for {payload.symbol} / {payload.timeframe}",
        )

    runner_input = json.dumps({
        "data": data,
        "user_code": payload.script,
        "initial_balance": payload.initial_balance,
        "commission_percent": payload.commission_percent,
        "slippage_percent": payload.slippage_percent,
    }).encode()

    container = None
    try:
        container = _docker.containers.create(
            RUNNER_IMAGE,
            stdin_open=True,
            network_disabled=True,
            mem_limit="512m",
            nano_cpus=int(1e9),
            pids_limit=200,
        )

        sock = container.attach_socket(params={"stdin": 1, "stream": 1})
        container.start()
        sock._sock.sendall(runner_input)
        sock._sock.shutdown(socket_module.SHUT_WR)

        try:
            container.wait(timeout=RUNNER_TIMEOUT)
        except Exception:
            raise HTTPException(status_code=408, detail="Strategy execution timed out (60s limit)")

        stdout_bytes = container.logs(stdout=True, stderr=False)

    except HTTPException:
        raise
    except docker_sdk.errors.ImageNotFound:
        raise HTTPException(
            status_code=500,
            detail=f"Runner image '{RUNNER_IMAGE}' not found. Run: docker build -f Dockerfile.runner -t devtrade-runner .",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Runner error: {e}")
    finally:
        if container:
            try:
                container.remove(force=True)
            except Exception:
                pass

    if not stdout_bytes:
        raise HTTPException(status_code=422, detail="Runner produced no output")

    try:
        output = json.loads(stdout_bytes)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Runner output is not valid JSON")

    if not output.get("ok"):
        raise HTTPException(status_code=422, detail=output.get("error", "Unknown error"))

    return {
        "symbol": payload.symbol,
        "timeframe": payload.timeframe,
        **output["result"],
    }


# TEST COMMAND (run from backend/sandbox):
# python3 -c "import json; close=[100,102,101,104,103,106,105,108,107,110,109,112,111,114,113,116,115,118,117,120,119,117,115,113,111,109,107,105,103,101]; payload={'data':{'open':[c-1 for c in close],'high':[c+1 for c in close],'low':[c-1 for c in close],'close':close,'volume':[1000]*30,'time':list(range(30))},'user_code':'\ndef strategy(open, high, low, close, volume, time):\n    ema5=ta.ema(close,5)\n    ema10=ta.ema(close,10)\n    return {\"long_entry\":crossover(ema5,ema10),\"long_exit\":crossunder(ema5,ema10)}\n','initial_balance':10000,'commission_percent':0.1,'slippage_percent':0.0}; print(json.dumps(payload))" | docker run --rm -i --network=none --memory=512m --cpus=1.0 --pids-limit=200 devtrade-runner
