import asyncio
import json
import time
import websockets
from fastapi import FastAPI, WebSocket
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

# Store latest prices and their timestamps
latest_prices = {
    "binance": {"price": 0.0, "timestamp": 0},
    "kraken": {"price": 0.0, "timestamp": 0},
    "bitstamp": {"price": 0.0, "timestamp": 0},
}

# Use only prices updated within the last 30 seconds
VALID_DURATION = 30

async def binance_ws():
    uri = "wss://stream.binance.com:9443/ws/btcusdt@trade"
    async for ws in websockets.connect(uri):
        try:
            async for msg in ws:
                data = json.loads(msg)
                price = float(data['p'])
                latest_prices["binance"] = {"price": price, "timestamp": time.time()}
        except Exception as e:
            print("Binance WS error:", e)
            await asyncio.sleep(5)

async def kraken_ws():
    uri = "wss://ws.kraken.com"
    subscribe_msg = {
        "event": "subscribe",
        "pair": ["XBT/USD"],
        "subscription": {"name": "trade"}
    }
    while True:
        try:
            async with websockets.connect(uri) as ws:
                await ws.send(json.dumps(subscribe_msg))
                async for msg in ws:
                    data = json.loads(msg)
                    if isinstance(data, list) and len(data) > 1 and data[1]:
                        price = float(data[1][0][0])
                        latest_prices["kraken"] = {"price": price, "timestamp": time.time()}
        except Exception as e:
            print("Kraken WS error:", e)
            await asyncio.sleep(5)

async def bitstamp_ws():
    uri = "wss://ws.bitstamp.net"
    subscribe_msg = {
        "event": "bts:subscribe",
        "data": {"channel": "live_trades_btcusd"}
    }
    while True:
        try:
            async with websockets.connect(uri) as ws:
                await ws.send(json.dumps(subscribe_msg))
                async for msg in ws:
                    data = json.loads(msg)
                    if data.get("event") == "trade":
                        price = float(data["data"]["price"])
                        latest_prices["bitstamp"] = {"price": price, "timestamp": time.time()}
        except Exception as e:
            print("Bitstamp WS error:", e)
            await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(binance_ws())
    asyncio.create_task(kraken_ws())
    asyncio.create_task(bitstamp_ws())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        await asyncio.sleep(1)
        now = time.time()
        valid_prices = [v["price"] for v in latest_prices.values() if now - v["timestamp"] <= VALID_DURATION and v["price"] > 0]
        avg_price = sum(valid_prices) / len(valid_prices) if valid_prices else 0.0

        sources = {k: v["price"] for k, v in latest_prices.items() if v["price"] > 0}
        await websocket.send_text(json.dumps({
            "price": round(avg_price, 2),
            "sources": sources
        }))

if __name__ == "__main__":
    uvicorn.run("btc_ws_proxy_backend:app", host="0.0.0.0", port=8000, reload=True)
