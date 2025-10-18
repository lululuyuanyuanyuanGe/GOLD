from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
import threading
import time

LOG_FILE = "news.txt"


def log_message(message):
    print(message)
    with open(LOG_FILE, "a") as f:
        f.write(message + "\n")

class IBApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.ready = threading.Event()
        self.news_subscriptions = {}

    def nextValidId(self, orderId):
        log_message(f"Connection successful. Next valid ID: {orderId}")
        self.ready.set()

    def newsProviders(self, newsProviders):
        provider_codes = [p.code for p in newsProviders]
        log_message(f"Available news providers: {provider_codes}")

    def tickNews(self, tickerId, timeStamp, providerCode, articleId, headline, extraData):
        news_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timeStamp))
        feed = self.news_subscriptions.get(tickerId, "Unknown")
        
        # Clean metadata from headline
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

    def error(self, reqId, code, msg, advancedOrderReject=""):
        # Filter out informational messages
        if code in [2104, 2107, 2157, 2106, 2158]:
            return
        log_message(f"ERROR {code}: {msg}")

    def subscribe_to_broadtape(self, provider_code):
        """Subscribe to BroadTape general market news"""
        log_message(f"Subscribing to {provider_code} BroadTape...")
        
        contract = Contract()
        contract.symbol = f"{provider_code}:{provider_code}_ALL"
        contract.secType = "NEWS"
        contract.exchange = provider_code
        
        req_id = 9000 + len(self.news_subscriptions)
        self.news_subscriptions[req_id] = f"{provider_code}_BroadTape"
        
        self.reqMktData(req_id, contract, "", False, False, [])
        return req_id

    
def main():
    # Clear the log file at the start of the session
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

        # Check available providers
        print("Checking news providers")
        app.reqNewsProviders()
        time.sleep(2)

        log_message("\n=== Subscribing to BroadTape News Feeds ===")
        
        # Subscribe to all free BroadTape feeds
        app.subscribe_to_broadtape("BRFG")   # Briefing.com general market
        time.sleep(1)
        app.subscribe_to_broadtape("DJNL")   # Dow Jones newsletters
        time.sleep(1)
        
        # If you have Benzinga subscription (paid):
        # app.subscribe_to_broadtape("BZ")
        
        log_message("\nListening for general market news...")
        log_message("NOTE: News only flows during market hours (Mon-Fri)")
        log_message("Press Ctrl+C to stop\n")
        
        while True:
            time.sleep(10)

    except KeyboardInterrupt:
        log_message("\nStopping...")
    finally:
        app.disconnect()
        log_message("Disconnected.")


if __name__ == "__main__":
    main()