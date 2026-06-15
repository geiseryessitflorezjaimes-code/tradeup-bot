from fastapi import FastAPI
from typing import Dict
from datetime import datetime

app = FastAPI()

trades = []

@app.get("/")
def home():
    return {
        "status": "TradeUp Bot Online",
        "mode": "SIMULATION",
        "version": "1.1"
    }

@app.post("/webhook")
async def webhook(data: Dict):
    now = datetime.now().isoformat()

    symbol = data.get("symbol", "MNQ")
    side = data.get("side", "")
    score = int(data.get("score", 0))

    h1 = data.get("h1", False)
    sweep = data.get("sweep", False)
    bos = data.get("bos", False)
    retest = data.get("retest", False)
    fvg = data.get("fvg", False)

   accepted = (
    score >= 80 and
    side in ["BUY", "SELL"]
)
    )

    trade = {
        "time": now,
        "symbol": symbol,
        "side": side,
        "score": score,
        "h1": h1,
        "sweep": sweep,
        "bos": bos,
        "retest": retest,
        "fvg": fvg,
        "accepted": accepted,
        "mode": "SIMULATION"
    }

    trades.append(trade)

    return {
        "success": True,
        "accepted": accepted,
        "message": "ENTRADA SIMULADA" if accepted else "SEÑAL BLOQUEADA",
        "trade": trade
    }

@app.get("/trades")
def get_trades():
    return {
        "total": len(trades),
        "trades": trades
    }
