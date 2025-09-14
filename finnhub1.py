import websocket
import json

# Enable verbose wire logging
websocket.enableTrace(True)

def on_message(ws, message):
    print("MSG:", message)

def on_error(ws, error):
    print("ERR:", error)

def on_close(ws, code, msg):
    print("CLOSE:", code, msg)

def on_open(ws):
    ws.send("Hello, Server")

ws = websocket.WebSocketApp(
    "wss://echo.websocket.events/",
    on_open=on_open,
    on_message=on_message,
    on_error=on_error,
    on_close=on_close,
)
ws.run_forever()

def on_open(ws):
    # Send valid JSON for each symbol; no stray newlines
    ws.send(json.dumps({"type":"subscribe-news","symbol":"AAPL"}))
    ws.send(json.dumps({"type":"subscribe-news","symbol":"AMZN"}))
    ws.send(json.dumps({"type":"subscribe-news","symbol":"MSFT"}))
    ws.send(json.dumps({"type":"subscribe-news","symbol":"BYND"}))

if __name__ == "__main__":
    # Optional: detailed wire debug
    websocket.enableTrace(True)
    ws = websocket.WebSocketApp(
        "wss://ws.finnhub.io?token=REDACTED_API_KEY",
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.run_forever()
