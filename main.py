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
        "version": "1.5"
    }

@app.post("/webhook")
async def webhook(data: Dict):
    now = datetime.now().isoformat()

    action = data.get("action", "OPEN")

    # CERRAR ÚLTIMA OPERACIÓN ABIERTA
    if action == "CLOSE":
        result = data.get("result", "PENDING")

        for trade in reversed(trades):
            if trade["status"] == "OPEN":
                trade["status"] = "CLOSED"
                trade["result"] = result
                trade["closed_time"] = now
                return {
                    "success": True,
                    "message": "OPERACIÓN CERRADA",
                    "trade": trade
                }

        return {
            "success": False,
            "message": "NO HAY OPERACIONES ABIERTAS"
        }

    # ABRIR OPERACIÓN SIMULADA
    symbol = data.get("symbol", "MNQ")
    side = data.get("side", "")
    score = int(data.get("score", 0))
    entry = float(data.get("price", 0))

    h1 = data.get("h1", False)
    sweep = data.get("sweep", False)
    bos = data.get("bos", False)
    retest = data.get("retest", False)
    fvg = data.get("fvg", False)

    already_open = any(
        t["symbol"] == symbol and
        t["status"] == "OPEN" and
        t["accepted"] == True
        for t in trades
    )

    accepted = (
        score >= 80 and
        side in ["BUY", "SELL"] and
        not already_open
    )

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
        "id": len(trades) + 1,
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
        "blocked_reason": "OPEN_TRADE_EXISTS" if already_open else None,
        "status": "OPEN" if accepted else "BLOCKED",
        "result": "PENDING",
        "mode": "SIMULATION"
    }

    trades.append(trade)

    return {
        "success": True,
        "accepted": accepted,
        "message": "ENTRADA SIMULADA ABIERTA" if accepted else "SEÑAL BLOQUEADA O YA EXISTE OPERACIÓN ABIERTA",
        "trade": trade
    }

@app.get("/trades")
def get_trades():
    return {
        "total": len(trades),
        "trades": trades
    }

@app.get("/open_trades")
def open_trades():
    open_list = [
        t for t in trades
        if t["status"] == "OPEN" and t["accepted"] == True
    ]

    return {
        "total_open": len(open_list),
        "open_trades": open_list
    }

@app.get("/stats")
def stats():
    total = len(trades)
    accepted = [t for t in trades if t["accepted"]]
    blocked = [t for t in trades if not t["accepted"]]
    closed = [t for t in accepted if t["status"] == "CLOSED"]
    open_trades_list = [t for t in accepted if t["status"] == "OPEN"]
    wins = [t for t in closed if t["result"] == "WIN"]
    losses = [t for t in closed if t["result"] == "LOSS"]

    win_rate = round((len(wins) / len(closed)) * 100, 2) if closed else 0

    return {
        "total_signals": total,
        "accepted_trades": len(accepted),
        "blocked_signals": len(blocked),
        "open_trades": len(open_trades_list),
        "closed_trades": len(closed),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": win_rate,
        "mode": "SIMULATION"
    }
