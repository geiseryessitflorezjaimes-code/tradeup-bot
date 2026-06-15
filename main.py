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
        "version": "1.6"
    }

def check_tp_sl(trade, current_price):
    if trade["status"] != "OPEN":
        return trade

    side = trade["side"]

    if side == "BUY":
        if current_price >= trade["tp1"]:
            trade["status"] = "CLOSED"
            trade["result"] = "WIN"
            trade["closed_price"] = current_price
            trade["closed_time"] = datetime.now().isoformat()
            trade["close_reason"] = "TP1_HIT"

        elif current_price <= trade["sl"]:
            trade["status"] = "CLOSED"
            trade["result"] = "LOSS"
            trade["closed_price"] = current_price
            trade["closed_time"] = datetime.now().isoformat()
            trade["close_reason"] = "SL_HIT"

    if side == "SELL":
        if current_price <= trade["tp1"]:
            trade["status"] = "CLOSED"
            trade["result"] = "WIN"
            trade["closed_price"] = current_price
            trade["closed_time"] = datetime.now().isoformat()
            trade["close_reason"] = "TP1_HIT"

        elif current_price >= trade["sl"]:
            trade["status"] = "CLOSED"
            trade["result"] = "LOSS"
            trade["closed_price"] = current_price
            trade["closed_time"] = datetime.now().isoformat()
            trade["close_reason"] = "SL_HIT"

    return trade

@app.post("/webhook")
async def webhook(data: Dict):
    now = datetime.now().isoformat()
    action = data.get("action", "OPEN")

    current_price = float(data.get("price", 0))

    # MONITOREAR OPERACIONES ABIERTAS
    if action == "UPDATE_PRICE":
        updated = []

        for trade in trades:
            if trade["status"] == "OPEN" and trade["accepted"] == True:
                updated_trade = check_tp_sl(trade, current_price)
                updated.append(updated_trade)

        return {
            "success": True,
            "message": "PRECIO ACTUALIZADO",
            "price": current_price,
            "updated": updated
        }

    # CIERRE MANUAL
    if action == "CLOSE":
        result = data.get("result", "PENDING")

        for trade in reversed(trades):
            if trade["status"] == "OPEN":
                trade["status"] = "CLOSED"
                trade["result"] = result
                trade["closed_time"] = now
                trade["closed_price"] = current_price
                trade["close_reason"] = "MANUAL_CLOSE"

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
    entry = current_price

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
        not already_open and
        entry > 0
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
        "message": "ENTRADA SIMULADA ABIERTA" if accepted else "SEÑAL BLOQUEADA",
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
