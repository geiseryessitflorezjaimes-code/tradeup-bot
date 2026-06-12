from fastapi import FastAPI
from typing import Dict

app = FastAPI()

@app.get("/")
def home():
    return {
        "status": "TradeUp Bot Online",
        "version": "1.0"
    }

@app.post("/webhook")
async def webhook(data: Dict):
    print("ALERTA RECIBIDA:", data)

    score = data.get("score", 0)

    if score >= 80:
        return {
            "success": True,
            "accepted": True,
            "message": "TradeUp aceptó la señal",
            "data": data
        }

    return {
        "success": True,
        "accepted": False,
        "message": "Score menor a 80",
        "data": data
    }
