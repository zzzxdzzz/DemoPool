from fastapi import WebSocket

active = set()

async def notify_ws(ws: WebSocket):
    await ws.accept()
    active.add(ws)
    try:
        while True:
            await ws.receive_text()  # 心跳占位
    except Exception:
        active.discard(ws)

async def broadcast(msg: str):
    for ws in list(active):
        try:
            await ws.send_text(msg)
        except Exception:
            active.discard(ws)
