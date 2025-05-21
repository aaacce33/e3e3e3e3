
import asyncio
import json
import websockets
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store latest price in memory
latest_price = {"binance": 0.0}

async def binance_ws():
    uri = "wss://stream.binance.com:9443/ws/btcusdt@trade"
    async for ws in websockets.connect(uri):
        try:
            async for msg in ws:
                data = json.loads(msg)
                price = float(data['p'])
                latest_price["binance"] = price
        except Exception as e:
            print("Binance connection error:", e)
            await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(binance_ws())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        await asyncio.sleep(1)
        await websocket.send_text(json.dumps({"price": latest_price["binance"]}))

if __name__ == "__main__":
    uvicorn.run("btc_ws_proxy_backend:app", host="0.0.0.0", port=8000, reload=True)
