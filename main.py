from fastapi import FastAPI
from typing import Dict
from datetime import datetime

app = FastAPI()

trades = []

SL_POINTS = 25
TP1_POINTS = 20
TP2_POINTS = 40

@app.get("/")
def home():
    return {
        "status": "TradeUp Bot Online",
        "mode": "SIMULATION",
        "version": "1.3"
    }

@app.post("/webhook")
async def webhook(data: Dict):
    now = datetime.now().isoformat()

    symbol = data.get("symbol", "MNQ")
    side = data.get("side", "")
    score = int(data.get("score", 0))
    entry = float(data.get("price", 0))

    h1 = data.get("h1", False)
    sweep = data.get("sweep", False)
    bos = data.get("bos", False)
    retest = data.get("retest", False)
    fvg = data.get("fvg", False)

    accepted = score >= 80 and side in ["BUY", "SELL"]

    if side == "BUY":
        sl = entry - SL_POINTS
        tp1 = entry + TP1_POINTS
        tp2 = entry + TP2_POINTS
    elif side == "SELL":
        sl = entry + SL_POINTS
        tp1 = entry - TP1_POINTS
        tp2 = entry - TP2_POINTS
    else:
        sl = 0
        tp1 = 0
        tp2 = 0

    trade = {
        "time": now,
        "symbol": symbol,
        "side": side,
        "score": score,
        "entry": entry,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "h1": h1,
        "sweep": sweep,
        "bos": bos,
        "retest": retest,
        "fvg": fvg,
        "accepted": accepted,
        "status": "OPEN" if accepted else "BLOCKED",
        "result": "PENDING",
        "mode": "SIMULATION"
    }

    trades.append(trade)
    print("TRADEUP SIGNAL:", trade)

    return {
        "success": True,
        "accepted": accepted,
        "message": "ENTRADA SIMULADA ABIERTA" if accepted else "SEÑAL BLOQUEADA",
        "trade": trade
    }

@app.get("/trades")
def get_trades():
    return {
        "total": len(trades),
        "trades": trades
    }

@app.get("/stats")
def stats():
    total = len(trades)
    accepted = len([t for t in trades if t["accepted"]])
    blocked = total - accepted

    return {
        "total_signals": total,
        "accepted_trades": accepted,
        "blocked_signals": blocked,
        "mode": "SIMULATION"
    }
