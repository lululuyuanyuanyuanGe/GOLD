from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.ticktype import TickTypeEnum
import threading
import time

LOG_FILE = "D:\\proejects\\Gold\\news"


def log_message(message):
    print(message)
    with open(LOG_FILE, "a") as f:
        f.write(message + "\n")

class IBApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.ready = threading.Event()
        # News
        self.news_subscriptions = {}
        # Market Data
        self.market_data_subscriptions = {}
        self.market_data = {}

    def nextValidId(self, orderId):
        log_message(f"Connection successful. Next valid ID: {orderId}")
        self.ready.set()

    # --- News Callbacks ---
    def newsProviders(self, newsProviders):
        provider_codes = [p.code for p in newsProviders]
        log_message(f"Available news providers: {provider_codes}")

    def tickNews(self, tickerId, timeStamp, providerCode, articleId, headline, extraData):
        news_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timeStamp))
        feed = self.news_subscriptions.get(tickerId, "Unknown")
        clean_headline = headline.split('!')[-1] if '!' in headline else headline
        news_output = (
            f"\n--- BROADTAPE NEWS ---\n"
            f"  Feed: {feed}\n"
            f"  Time: {news_time}\n"
            f"  Provider: {providerCode}\n"
            f"  Headline: {clean_headline}\n"
            f"----------------------"
        )
        log_message(news_output)

    # --- Market Data Callbacks ---
    def tickPrice(self, reqId, tickType, price, attrib):
        if price <= 0:
            return
        symbol = self.market_data_subscriptions.get(reqId)
        if not symbol: return

        tick_type_str = TickTypeEnum.to_str(tickType)
        log_message(f"--- PRICE --- [{symbol}] {tick_type_str}: {price}")
        if symbol not in self.market_data:
            self.market_data[symbol] = {}
        self.market_data[symbol][tick_type_str] = price

    def realtimeBar(self, reqId, time, open_, high, low, close, volume, wap, count):
        symbol = self.market_data_subscriptions.get(reqId)
        if not symbol: return

        bar = {"time": time, "open": open_, "high": high, "low": low, "close": close, "volume": volume}
        log_message(f"--- 5-SEC BAR --- [{symbol}] O:{open_} H:{high} L:{low} C:{close} V:{volume}")
        if symbol not in self.market_data:
            self.market_data[symbol] = {}
        self.market_data[symbol]["bar"] = bar

    def error(self, reqId, code, msg, advancedOrderReject=""):
        if code in [2104, 2107, 2157, 2106, 2158]:
            return
        log_message(f"ERROR {code}: {msg}")

    # --- Subscription Methods ---
    def subscribe_to_broadtape(self, provider_code):
        log_message(f"Subscribing to {provider_code} BroadTape...")
        contract = Contract()
        contract.symbol = f"{provider_code}:{provider_code}_ALL"
        contract.secType = "NEWS"
        contract.exchange = provider_code
        req_id = 9000 + len(self.news_subscriptions)
        self.news_subscriptions[req_id] = f"{provider_code}_BroadTape"
        self.reqMktData(req_id, contract, "", False, False, [])
        return req_id

    def subscribe_to_market_data(self, symbol):
        log_message(f"\n=== Subscribing to Market Data for {symbol} ===")
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"

        # Generate unique request IDs
        base_req_id = 2000 + (len(self.market_data_subscriptions) * 10)
        price_req_id = base_req_id + 1
        bar_req_id = base_req_id + 2

        self.market_data_subscriptions[price_req_id] = symbol
        self.market_data_subscriptions[bar_req_id] = symbol

        # Request price ticks
        self.reqMktData(price_req_id, contract, "", False, False, [])
        log_message(f"Subscribed to price data for {symbol} with ID {price_req_id}")

        # Request 5-second bars
        self.reqRealTimeBars(bar_req_id, contract, 5, "TRADES", True, [])
        log_message(f"Subscribed to 5-sec bars for {symbol} with ID {bar_req_id}")

def main():
    with open(LOG_FILE, "w") as f:
        f.write("Starting new session...\n")

    app = IBApp()
    try:
        app.connect("127.0.0.1", 4001, 1)
        log_message("Connecting to IBKR Gateway...")
        
        pump = threading.Thread(target=app.run, daemon=True)
        pump.start()
        
        if not app.ready.wait(timeout=10):
            log_message("Connection timeout.")
            return

        # --- Market Data Subscription ---
        app.subscribe_to_market_data("AAPL")
        time.sleep(2)

        # --- News Subscription ---
        app.reqNewsProviders()
        time.sleep(2)
        log_message("\n=== Subscribing to BroadTape News Feeds ===")
        app.subscribe_to_broadtape("BRFG")
        time.sleep(1)
        app.subscribe_to_broadtape("DJNL")
        time.sleep(1)
        
        log_message("\nListening for data... Press Ctrl+C to stop\n")
        
        while True:
            time.sleep(10)
            # Periodically print the latest market data we have
            if "AAPL" in app.market_data:
                log_message(f"\n--- LATEST AAPL DATA ---")
                log_message(str(app.market_data["AAPL"]))
                log_message("------------------------\n")

    except KeyboardInterrupt:
        log_message("\nStopping...")
    finally:
        app.disconnect()
        log_message("Disconnected.")

if __name__ == "__main__":
    main()
