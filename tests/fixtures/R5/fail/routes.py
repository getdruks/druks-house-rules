async def stream(window, websocket) -> None:
    try:
        await window.stream(websocket)
    except Exception:
        await websocket.close(code=1011)
    try:
        await websocket.close()
    except:
        pass
