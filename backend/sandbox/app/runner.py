import sys
import json

from backtester import run_backtest


def main():
    try:
        payload = json.loads(sys.stdin.buffer.read())
    except Exception as e:
        print(json.dumps({"ok": False, "error": f"Invalid input: {e}"}))
        sys.exit(1)

    try:
        result = run_backtest(
            data=payload["data"],
            user_code=payload["user_code"],
            initial_balance=payload.get("initial_balance", 10000),
            commission_percent=payload.get("commission_percent", 0.1),
            slippage_percent=payload.get("slippage_percent", 0.0),
        )
        print(json.dumps({"ok": True, "result": result}))
    except ValueError as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"ok": False, "error": f"Strategy error: {e}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
