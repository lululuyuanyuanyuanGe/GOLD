from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.ticktype import TickTypeEnum
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
        self.next_req_id_val = 1 # Initialize a counter for request IDs
        # News
        self.news_subscriptions = {}
        self.historical_news = {} # To store historical news
        self.pending_news_requests = {} # To store pending news requests for contract resolution
        self.contract_details = {} # To store contract details after resolution
        # Market Data
        self.market_data_subscriptions = {}
        self.market_data = {}

    def nextValidId(self, orderId: int):
        log_message(f"Connection successful. Next valid ID: {orderId}")
        self.ready.set()
        self.next_req_id_val = orderId # Initialize with the valid ID from IBKR

    def next_req_id(self) -> int:
        self.next_req_id_val += 1
        return self.next_req_id_val

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

    def historicalNews(self, reqId: int, time: str, providerCode: str, articleId: str, headline: str):
        if reqId not in self.historical_news:
            self.historical_news[reqId] = []
        self.historical_news[reqId].append({
            "time": time,
            "providerCode": providerCode,
            "articleId": articleId,
            "headline": headline
        })

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

    def get_latest_news(self, symbol: str, providers: str = "BRFG+DJNL", num_articles: int = 10):
        """
        Request a specific number of the latest news articles for a stock.

        :param symbol: The stock symbol (e.g., "AAPL").
        :param providers: Provider codes (e.g., "BRFG+DJNL"). Defaults to free providers.
        :param num_articles: The number of articles to fetch.
        """
        log_message(f"\n=== Requesting {num_articles} Latest News for {symbol} from providers: '{providers}' ===")
        
        # Step 1: Create a stock contract (NOT a NEWS contract)
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"          # ← CHANGED: Must be "STK" for stocks, not "NEWS"
        contract.exchange = "SMART"
        contract.currency = "USD"
        
        # Step 2: Request contract details to get the conId
        detail_req_id = 8000 + len(self.contract_details)
        self.reqContractDetails(detail_req_id, contract)
        
        log_message(f"Requesting contract details for {symbol}...")
        time.sleep(2)  # Wait for contractDetails callback
        
        # Step 3: Check if we got the contract details
        if detail_req_id not in self.contract_details:
            log_message(f"ERROR: Could not retrieve contract details for {symbol}")
            return None
        
        # Step 4: Extract the conId from the stored contract
        conId = self.contract_details[detail_req_id].conId
        log_message(f"Got conId {conId} for {symbol}")
        
        # Step 5: Request historical news with CORRECT syntax
        query_id = detail_req_id + 1000
        self.historical_news[query_id] = []  # Initialize storage for this request
        
        self.reqHistoricalNews(
            query_id,         # reqId (int) - unique identifier
            conId,            # conId (int) - the contract ID we just retrieved
            providers,        # providerCodes (str) - e.g., "BRFG+DJNL"
            "",               # startDateTime (str) - empty for default lookback
            "",               # endDateTime (str) - empty for now
            num_articles,     # totalResults (int) - number of articles
            []                # historicalNewsOptions (list) - always []
        )
        
        log_message(f"Requested {num_articles} latest news articles for {symbol} with ID {query_id}")
        return query_id

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

        # --- Fetch Latest News for a Stock ---
        aapl_news_req_id = app.get_latest_news("AAPL")
        time.sleep(5) # Give some time for news to arrive
        if aapl_news_req_id in app.historical_news:
            log_message(f"\n--- LATEST NEWS FOR AAPL ---")
            for article in app.historical_news[aapl_news_req_id]:
                log_message(f"  Time: {article["time"]}\n  Provider: {article["providerCode"]}\n  Headline: {article["headline"]}")
            log_message("----------------------------\n")

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
