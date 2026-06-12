from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"status": "TradeUp Bot Online"}

@app.post("/webhook")
async def webhook(data: dict):
    print("ALERTA RECIBIDA:", data)

    return {
        "success": True,
        "message": "TradeUp recibió la señal",
        "data": data
    }
