import exceptions


async def stream(window, websocket) -> None:
    try:
        await window.stream(websocket)
    except exceptions.BrowserApiError:
        await websocket.close(code=1011)
