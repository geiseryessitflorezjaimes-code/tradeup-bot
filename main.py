from fastapi import FastAPI
from fastapi.responses import HTMLResponse
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
        "version": "1.7",
        "dashboard": "/dashboard"
    }

def check_tp_sl(trade, current_price):
    if trade["status"] != "OPEN":
        return trade

    if trade["side"] == "BUY":
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

    if trade["side"] == "SELL":
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

    if action == "UPDATE_PRICE":
        updated = []
        for trade in trades:
            if trade["status"] == "OPEN" and trade["accepted"] == True:
                updated.append(check_tp_sl(trade, current_price))

        return {
            "success": True,
            "message": "PRECIO ACTUALIZADO",
            "price": current_price,
            "updated": updated
        }

    if action == "CLOSE":
        result = data.get("result", "PENDING")
        for trade in reversed(trades):
            if trade["status"] == "OPEN":
                trade["status"] = "CLOSED"
                trade["result"] = result
                trade["closed_time"] = now
                trade["closed_price"] = current_price
                trade["close_reason"] = "MANUAL_CLOSE"
                return {"success": True, "message": "OPERACIÓN CERRADA", "trade": trade}
        return {"success": False, "message": "NO HAY OPERACIONES ABIERTAS"}

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
        t["symbol"] == symbol and t["status"] == "OPEN" and t["accepted"] == True
        for t in trades
    )

    accepted = score >= 80 and side in ["BUY", "SELL"] and not already_open and entry > 0

    if side == "BUY":
        sl = entry - SL_POINTS
        tp1 = entry + TP1_POINTS
        tp2 = entry + TP2_POINTS
    elif side == "SELL":
        sl = entry + SL_POINTS
        tp1 = entry - TP1_POINTS
        tp2 = entry - TP2_POINTS
    else:
        sl, tp1, tp2 = 0, 0, 0

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
    return {"success": True, "accepted": accepted, "trade": trade}

@app.get("/trades")
def get_trades():
    return {"total": len(trades), "trades": trades}

@app.get("/open_trades")
def open_trades():
    open_list = [t for t in trades if t["status"] == "OPEN" and t["accepted"] == True]
    return {"total_open": len(open_list), "open_trades": open_list}

@app.get("/stats")
def stats():
    total = len(trades)
    accepted = [t for t in trades if t["accepted"]]
    blocked = [t for t in trades if not t["accepted"]]
    closed = [t for t in accepted if t["status"] == "CLOSED"]
    open_list = [t for t in accepted if t["status"] == "OPEN"]
    wins = [t for t in closed if t["result"] == "WIN"]
    losses = [t for t in closed if t["result"] == "LOSS"]
    win_rate = round((len(wins) / len(closed)) * 100, 2) if closed else 0

    return {
        "total_signals": total,
        "accepted_trades": len(accepted),
        "blocked_signals": len(blocked),
        "open_trades": len(open_list),
        "closed_trades": len(closed),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": win_rate,
        "mode": "SIMULATION"
    }

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    accepted = [t for t in trades if t["accepted"]]
    closed = [t for t in accepted if t["status"] == "CLOSED"]
    open_list = [t for t in accepted if t["status"] == "OPEN"]
    wins = [t for t in closed if t["result"] == "WIN"]
    losses = [t for t in closed if t["result"] == "LOSS"]
    win_rate = round((len(wins) / len(closed)) * 100, 2) if closed else 0

    rows = ""
    markers = []

    for t in trades[-20:]:
        status_color = "#22c55e" if t["result"] == "WIN" else "#ef4444" if t["result"] == "LOSS" else "#f59e0b" if t["status"] == "OPEN" else "#64748b"
        rows += f"""
        <tr>
            <td>{t['id']}</td>
            <td>{t['symbol']}</td>
            <td class="{t['side'].lower()}">{t['side']}</td>
            <td>{t['score']}</td>
            <td>{t['entry']}</td>
            <td>{t['sl']}</td>
            <td>{t['tp1']}</td>
            <td>{t['status']}</td>
            <td style="color:{status_color};font-weight:bold;">{t['result']}</td>
        </tr>
        """
        if t["accepted"]:
            markers.append(t)

    last_trade = markers[-1] if markers else None
    entry = last_trade["entry"] if last_trade else 0
    sl = last_trade["sl"] if last_trade else 0
    tp1 = last_trade["tp1"] if last_trade else 0
    tp2 = last_trade["tp2"] if last_trade else 0
    side = last_trade["side"] if last_trade else "WAIT"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>TradeUp Dashboard</title>
        <script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
        <style>
            body {{
                margin:0;
                background:#0f172a;
                color:white;
                font-family:Arial, sans-serif;
            }}
            .header {{
                padding:20px;
                background:#020617;
                display:flex;
                justify-content:space-between;
                align-items:center;
            }}
            .title {{
                font-size:28px;
                font-weight:bold;
            }}
            .mode {{
                background:#1e293b;
                padding:8px 14px;
                border-radius:8px;
                color:#38bdf8;
            }}
            .cards {{
                display:grid;
                grid-template-columns:repeat(7,1fr);
                gap:12px;
                padding:20px;
            }}
            .card {{
                background:#1e293b;
                padding:16px;
                border-radius:12px;
                text-align:center;
            }}
            .card h3 {{
                margin:0;
                font-size:13px;
                color:#94a3b8;
            }}
            .card p {{
                margin:8px 0 0;
                font-size:24px;
                font-weight:bold;
            }}
            .main {{
                display:grid;
                grid-template-columns:2fr 1fr;
                gap:20px;
                padding:20px;
            }}
            #chart {{
                height:420px;
                background:#020617;
                border-radius:12px;
            }}
            .panel {{
                background:#1e293b;
                padding:18px;
                border-radius:12px;
            }}
            table {{
                width:calc(100% - 40px);
                margin:20px;
                border-collapse:collapse;
                background:#1e293b;
                border-radius:12px;
                overflow:hidden;
            }}
            th, td {{
                padding:10px;
                border-bottom:1px solid #334155;
                text-align:center;
                font-size:13px;
            }}
            th {{
                color:#93c5fd;
                background:#020617;
            }}
            .buy {{
                color:#22c55e;
                font-weight:bold;
            }}
            .sell {{
                color:#ef4444;
                font-weight:bold;
            }}
            .check {{
                color:#22c55e;
            }}
            .no {{
                color:#ef4444;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="title">TRADEUP DASHBOARD</div>
            <div class="mode">SIMULATION v1.7</div>
        </div>

        <div class="cards">
            <div class="card"><h3>Total</h3><p>{len(trades)}</p></div>
            <div class="card"><h3>Aceptadas</h3><p>{len(accepted)}</p></div>
            <div class="card"><h3>Abiertas</h3><p>{len(open_list)}</p></div>
            <div class="card"><h3>Cerradas</h3><p>{len(closed)}</p></div>
            <div class="card"><h3>Wins</h3><p>{len(wins)}</p></div>
            <div class="card"><h3>Losses</h3><p>{len(losses)}</p></div>
            <div class="card"><h3>Win Rate</h3><p>{win_rate}%</p></div>
        </div>

        <div class="main">
            <div id="chart"></div>

            <div class="panel">
                <h2>Última operación</h2>
                <p><b>Dirección:</b> {side}</p>
                <p><b>Entry:</b> {entry}</p>
                <p><b>SL:</b> {sl}</p>
                <p><b>TP1:</b> {tp1}</p>
                <p><b>TP2:</b> {tp2}</p>
                <hr>
                <p>H1: <span class="check">{'✅' if last_trade and last_trade['h1'] else '❌'}</span></p>
                <p>Sweep: <span class="check">{'✅' if last_trade and last_trade['sweep'] else '❌'}</span></p>
                <p>BOS: <span class="check">{'✅' if last_trade and last_trade['bos'] else '❌'}</span></p>
                <p>Retest: <span class="check">{'✅' if last_trade and last_trade['retest'] else '❌'}</span></p>
                <p>FVG: <span class="check">{'✅' if last_trade and last_trade['fvg'] else '❌'}</span></p>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>ID</th><th>Symbol</th><th>Side</th><th>Score</th><th>Entry</th><th>SL</th><th>TP1</th><th>Status</th><th>Result</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>

        <script>
            const chart = LightweightCharts.createChart(document.getElementById('chart'), {{
                layout: {{
                    background: {{ color: '#020617' }},
                    textColor: '#cbd5e1'
                }},
                grid: {{
                    vertLines: {{ color: '#1e293b' }},
                    horzLines: {{ color: '#1e293b' }}
                }},
                width: document.getElementById('chart').clientWidth,
                height: 420
            }});

            const lineSeries = chart.addLineSeries({{
                color: side === 'BUY' ? '#22c55e' : '#ef4444',
                lineWidth: 2
            }});

            const base = {entry if entry else 100};
            const data = [
                {{ time: 1, value: base - 20 }},
                {{ time: 2, value: base - 10 }},
                {{ time: 3, value: base }},
                {{ time: 4, value: base + 8 }},
                {{ time: 5, value: base + 15 }},
                {{ time: 6, value: base + 22 }}
            ];

            lineSeries.setData(data);

            const entryLine = lineSeries.createPriceLine({{
                price: {entry},
                color: '#38bdf8',
                lineWidth: 2,
                lineStyle: 2,
                axisLabelVisible: true,
                title: 'ENTRY'
            }});

            const slLine = lineSeries.createPriceLine({{
                price: {sl},
                color: '#ef4444',
                lineWidth: 2,
                lineStyle: 2,
                axisLabelVisible: true,
                title: 'SL'
            }});

            const tp1Line = lineSeries.createPriceLine({{
                price: {tp1},
                color: '#22c55e',
                lineWidth: 2,
                lineStyle: 2,
                axisLabelVisible: true,
                title: 'TP1'
            }});

            const tp2Line = lineSeries.createPriceLine({{
                price: {tp2},
                color: '#84cc16',
                lineWidth: 2,
                lineStyle: 2,
                axisLabelVisible: true,
                title: 'TP2'
            }});

            window.addEventListener('resize', () => {{
                chart.applyOptions({{ width: document.getElementById('chart').clientWidth }});
            }});
        </script>
    </body>
    </html>
    """

    return HTMLResponse(content=html)
