from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from typing import Dict
from datetime import datetime

app = FastAPI()
trades = []
signals = []

SL_POINTS = 25
TP1_POINTS = 20
TP2_POINTS = 40
MIN_SCORE = 80

@app.get("/")
def home():
    return {
        "status": "TradeUp Bot Online",
        "mode": "SIMULATION",
        "version": "1.9.1",
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
        if current_price <= 0:
            return {
                "success": False,
                "message": "PRECIO INVALIDO",
                "price": current_price
            }

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

    signal = {
        "id": len(signals) + 1,
        "time": now,
        "symbol": symbol,
        "side": side,
        "score": score,
        "price": entry,
        "h1": h1,
        "sweep": sweep,
        "bos": bos,
        "retest": retest,
        "fvg": fvg
    }
    signals.append(signal)

    if entry <= 0:
        return {
            "success": False,
            "accepted": False,
            "message": "SEÑAL IGNORADA: PRICE 0",
            "signal": signal
        }

    already_open = any(
        t["symbol"] == symbol and t["status"] == "OPEN" and t["accepted"] == True
        for t in trades
    )

    accepted = score >= MIN_SCORE and side in ["BUY", "SELL"] and not already_open

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

@app.get("/signals")
def get_signals():
    return {"total": len(signals), "signals": signals}

@app.get("/open_trades")
def open_trades():
    open_list = [t for t in trades if t["status"] == "OPEN" and t["accepted"] == True]
    return {"total_open": len(open_list), "open_trades": open_list}

@app.get("/stats")
def stats():
    accepted = [t for t in trades if t["accepted"]]
    real_trades = [t for t in accepted if t["entry"] > 0]
    closed = [t for t in real_trades if t["status"] == "CLOSED"]
    open_list = [t for t in real_trades if t["status"] == "OPEN"]

    wins = [t for t in closed if t["result"] == "WIN"]
    losses = [t for t in closed if t["result"] == "LOSS"]

    win_rate = round((len(wins) / len(closed)) * 100, 2) if closed else 0

    gross_profit = len(wins) * TP1_POINTS
    gross_loss = len(losses) * SL_POINTS
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else gross_profit

    expectancy = round(
        ((len(wins) * TP1_POINTS) - (len(losses) * SL_POINTS)) / len(closed),
        2
    ) if closed else 0

    max_win_streak = 0
    max_loss_streak = 0
    current_win = 0
    current_loss = 0

    for t in closed:
        if t["result"] == "WIN":
            current_win += 1
            current_loss = 0
        elif t["result"] == "LOSS":
            current_loss += 1
            current_win = 0

        max_win_streak = max(max_win_streak, current_win)
        max_loss_streak = max(max_loss_streak, current_loss)

    valid_signals = [s for s in signals if s["price"] > 0]

    return {
        "total_signals": len(valid_signals),
        "total_trades": len(real_trades),
        "accepted_trades": len(real_trades),
        "open_trades": len(open_list),
        "closed_trades": len(closed),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "expectancy": expectancy,
        "max_win_streak": max_win_streak,
        "max_loss_streak": max_loss_streak,
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
    real_trades = [t for t in accepted if t["entry"] > 0]
    valid_signals = [s for s in signals if s["price"] > 0]

    gross_profit = len(wins) * TP1_POINTS
    gross_loss = len(losses) * SL_POINTS
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else gross_profit

    expectancy = round(
        ((len(wins) * TP1_POINTS) - (len(losses) * SL_POINTS)) / len(closed),
        2
    ) if closed else 0
    last_signal = signals[-1] if signals else None
    last_trade = accepted[-1] if accepted else None

    entry = last_trade["entry"] if last_trade else 0
    sl = last_trade["sl"] if last_trade else 0
    tp1 = last_trade["tp1"] if last_trade else 0
    tp2 = last_trade["tp2"] if last_trade else 0
    side = last_trade["side"] if last_trade else "WAIT"
    score = last_trade["score"] if last_trade else 0
    trade_result = last_trade["result"] if last_trade else "WAIT"
    last_signal_side = last_signal["side"] if last_signal else "WAIT"
    last_signal_score = last_signal["score"] if last_signal else 0

    risk_pts = abs(entry - sl) if entry and sl else 0
    tp1_pts = abs(tp1 - entry) if entry and tp1 else 0
    tp2_pts = abs(tp2 - entry) if entry and tp2 else 0

    status_bg = (
        "#22c55e" if trade_result == "WIN"
        else "#ef4444" if trade_result == "LOSS"
        else "#f59e0b" if last_trade and last_trade["status"] == "OPEN"
        else "#64748b"
    )

    rows = ""
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
            <td>{t['tp2']}</td>
            <td>{t['status']}</td>
            <td style="color:{status_color};font-weight:bold;">{t['result']}</td>
        </tr>
        """

    signal_rows = ""
    for s in signals[-10:]:
        signal_rows += f"""
        <tr>
            <td>{s['id']}</td>
            <td>{s['symbol']}</td>
            <td class="{s['side'].lower()}">{s['side']}</td>
            <td>{s['score']}</td>
            <td>{s['price']}</td>
            <td>{s['time']}</td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>TradeUp Dashboard Pro</title>
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
                font-weight:bold;
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
            .box {{
                background:#0f172a;
                padding:12px;
                border-radius:10px;
                margin-bottom:15px;
                border:1px solid #334155;
            }}
            .box h3 {{
                margin-top:0;
                color:#38bdf8;
            }}
            .score {{
                font-size:24px;
                font-weight:bold;
                color:#22c55e;
            }}
            .badge {{
                padding:6px 10px;
                border-radius:6px;
                color:white;
                font-weight:bold;
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
            .section-title {{
                margin:20px;
                color:#38bdf8;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="title">TRADEUP DASHBOARD PRO</div>
            <div class="mode">SIMULATION v1.9.1</div>
        </div>

     <div class="cards">
    <div class="card"><h3>Señales</h3><p>{len(valid_signals)}</p></div>
    <div class="card"><h3>Trades</h3><p>{len(real_trades)}</p></div>
    <div class="card"><h3>Abiertas</h3><p>{len(open_list)}</p></div>
    <div class="card"><h3>Cerradas</h3><p>{len(closed)}</p></div>
    <div class="card"><h3>Wins</h3><p>{len(wins)}</p></div>
    <div class="card"><h3>Profit Factor</h3><p>{profit_factor}</p></div>
    <div class="card"><h3>Expectancy</h3><p>{expectancy}</p></div>
</div>

        <div class="main">
            <div id="chart"></div>

            <div class="panel">
                <div class="box">
                    <h3>BOT STATUS</h3>
                    <p>🟢 <b>BOT ONLINE</b></p>
                    <p>📡 <b>WEBHOOK:</b> ACTIVO</p>
                    <p>🎯 <b>SCORE MÍNIMO:</b> {MIN_SCORE}</p>
                    <p>📈 <b>ÚLTIMA SEÑAL:</b> {last_signal_side}</p>
                    <p>⭐ <b>SCORE SEÑAL:</b> {last_signal_score}/100</p>
                </div>

                <h2>Último trade real</h2>
                <p><b>Dirección:</b> {side}</p>
                <p><b>Trade Score:</b> <span class="score">{score}/100</span></p>
                <p><b>Trade Status:</b> <span class="badge" style="background:{status_bg};">{trade_result}</span></p>
                <p><b>Entry:</b> {entry}</p>
                <p><b>SL:</b> {sl}</p>
                <p><b>TP1:</b> {tp1}</p>
                <p><b>TP2:</b> {tp2}</p>

                <hr>

                <div class="box">
                    <h3>RISK / REWARD</h3>
                    <p>⚠️ Riesgo: <b>{risk_pts}</b> pts</p>
                    <p>🎯 TP1: <b>{tp1_pts}</b> pts</p>
                    <p>🚀 TP2: <b>{tp2_pts}</b> pts</p>
                </div>

                <hr>

                <p>H1: {'✅' if last_trade and last_trade['h1'] else '❌'}</p>
                <p>Sweep: {'✅' if last_trade and last_trade['sweep'] else '❌'}</p>
                <p>BOS: {'✅' if last_trade and last_trade['bos'] else '❌'}</p>
                <p>Retest: {'✅' if last_trade and last_trade['retest'] else '❌'}</p>
                <p>FVG: {'✅' if last_trade and last_trade['fvg'] else '❌'}</p>
            </div>
        </div>

        <h2 class="section-title">Historial de trades reales</h2>
        <table>
            <thead>
                <tr>
                    <th>ID</th><th>Symbol</th><th>Side</th><th>Score</th><th>Entry</th><th>SL</th><th>TP1</th><th>TP2</th><th>Status</th><th>Result</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>

        <h2 class="section-title">Últimas señales recibidas</h2>
        <table>
            <thead>
                <tr>
                    <th>ID</th><th>Symbol</th><th>Side</th><th>Score</th><th>Price</th><th>Time</th>
                </tr>
            </thead>
            <tbody>{signal_rows}</tbody>
        </table>

        <script>
            const tradeSide = "{side}";
            const entryPrice = Number({entry});
            const slPrice = Number({sl});
            const tp1Price = Number({tp1});
            const tp2Price = Number({tp2});

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
                color: tradeSide === 'BUY' ? '#22c55e' : '#ef4444',
                lineWidth: 3
            }});

            let data = [];

            if (tradeSide === "SELL") {{
                data = [
                    {{ time: 1, value: entryPrice + 20 }},
                    {{ time: 2, value: entryPrice + 10 }},
                    {{ time: 3, value: entryPrice }},
                    {{ time: 4, value: entryPrice - 10 }},
                    {{ time: 5, value: tp1Price }},
                    {{ time: 6, value: tp2Price }}
                ];
            }} else if (tradeSide === "BUY") {{
                data = [
                    {{ time: 1, value: entryPrice - 20 }},
                    {{ time: 2, value: entryPrice - 10 }},
                    {{ time: 3, value: entryPrice }},
                    {{ time: 4, value: entryPrice + 10 }},
                    {{ time: 5, value: tp1Price }},
                    {{ time: 6, value: tp2Price }}
                ];
            }} else {{
                data = [
                    {{ time: 1, value: 100 }},
                    {{ time: 2, value: 100 }},
                    {{ time: 3, value: 100 }}
                ];
            }}

            lineSeries.setData(data);

            if (tradeSide === "BUY" || tradeSide === "SELL") {{
                lineSeries.setMarkers([
                    {{
                        time: 3,
                        position: tradeSide === "BUY" ? "belowBar" : "aboveBar",
                        color: tradeSide === "BUY" ? "#22c55e" : "#ef4444",
                        shape: tradeSide === "BUY" ? "arrowUp" : "arrowDown",
                        text: tradeSide + " ENTRY"
                    }}
                ]);

                lineSeries.createPriceLine({{ price: entryPrice, color: '#38bdf8', lineWidth: 2, lineStyle: 2, axisLabelVisible: true, title: 'ENTRY' }});
                lineSeries.createPriceLine({{ price: slPrice, color: '#ef4444', lineWidth: 2, lineStyle: 2, axisLabelVisible: true, title: 'SL' }});
                lineSeries.createPriceLine({{ price: tp1Price, color: '#22c55e', lineWidth: 2, lineStyle: 2, axisLabelVisible: true, title: 'TP1' }});
                lineSeries.createPriceLine({{ price: tp2Price, color: '#84cc16', lineWidth: 2, lineStyle: 2, axisLabelVisible: true, title: 'TP2' }});
            }}

            chart.timeScale().fitContent();

            window.addEventListener('resize', () => {{
                chart.applyOptions({{ width: document.getElementById('chart').clientWidth }});
            }});

            setTimeout(() => {{
                window.location.reload();
            }}, 3000);
        </script>
    </body>
    </html>
    """

    return HTMLResponse(content=html)
