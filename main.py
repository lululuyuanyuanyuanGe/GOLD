from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
import threading
import time
from datetime import datetime, timedelta


class IBApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.ready = threading.Event()
        self.news_subscriptions = {}
        self.company_news = {}
        self.contract_details = {}

    def nextValidId(self, orderId):
        print(f"Connection successful. Next valid ID: {orderId}")
        self.ready.set()

    def newsProviders(self, newsProviders):
        provider_codes = [p.code for p in newsProviders]
        print(f"Available news providers: {provider_codes}")
        if not provider_codes:
            print("WARNING: No news providers available. Check account subscriptions.")

    def tickNews(self, tickerId, timeStamp, providerCode, articleId, headline, extraData):
        news_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timeStamp))
        symbol = self.news_subscriptions.get(tickerId, "BroadTape")
        print(f"\n--- REAL-TIME NEWS ---")
        print(f"  Feed: {symbol}")
        print(f"  Time: {news_time}")
        print(f"  Provider: {providerCode}")
        print(f"  Headline: {headline}")
        print("----------------------")

    def historicalNews(self, requestId, time, providerCode, articleId, headline):
        symbol = self.news_subscriptions.get(requestId, "Historical")
        print(f"\n--- HISTORICAL NEWS ---")
        print(f"  Symbol: {symbol}")
        print(f"  Time: {time}")
        print(f"  Provider: {providerCode}")
        print(f"  Headline: {headline}")
        print("-----------------------")

    def newsArticle(self, requestId, articleType, articleText):
        print(f"\n--- NEWS ARTICLE ---")
        print(f"  Request ID: {requestId}")
        print(f"  Article Type: {articleType}")
        print(f"  Article Text: {articleText[:500]}...")
        print("--------------------")

    def contractDetails(self, reqId, contractDetails):
        print(f"Received contract details for request {reqId}")
        self.contract_details[reqId] = contractDetails.contract

    def contractDetailsEnd(self, reqId):
        print(f"Finished receiving contract details for request {reqId}")

    def error(self, reqId, code, msg, advancedOrderReject=""):
        # Filter out informational messages
        if code in [2104, 2107, 2157, 2106, 2158]:
            return  # Suppress connection status messages
        print(f"\n--- ERROR ---")
        print(f"  Request ID: {reqId}")
        print(f"  Error Code: {code}")
        print(f"  Message: {msg}")
        print("-------------")

    def subscribe_to_broadtape_news(self, provider="BRFG"):
        """Subscribe to general market news (NOT ticker-specific)"""
        print(f"Subscribing to {provider} BroadTape news...")
        
        contract = Contract()
        contract.symbol = f"{provider}:{provider}_ALL"
        contract.secType = "NEWS"
        contract.exchange = provider
        
        req_id = 9000 + len(self.news_subscriptions)
        self.news_subscriptions[req_id] = f"{provider}_BroadTape"
        
        # Empty generic tick list for NEWS contracts
        self.reqMktData(req_id, contract, "", False, False, [])
        return req_id

    def get_historical_news(self, symbol, days_back=7, max_results=50, provider="BRFG+BRFUPDN+DJNL"):
        """Get historical news for a specific ticker"""
        print(f"Requesting historical news for {symbol}...")
        
        req_id = len(self.news_subscriptions) + 100
        # Store with the historical request ID (req_id + 1000), not the contract detail ID
        
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"
        
        self.reqContractDetails(req_id, contract)
        print(f"Waiting for contract details for {symbol}...")
        time.sleep(3)
        
        if req_id in self.contract_details:
            contract_id = self.contract_details[req_id].conId
            print(f"Contract ID for {symbol} is {contract_id}")
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            start_str = start_date.strftime("%Y%m%d %H:%M:%S")
            end_str = end_date.strftime("%Y%m%d %H:%M:%S")
            
            print(f"Requesting news from {start_str} to {end_str}")
            
            # Store the symbol with the historical news request ID
            hist_req_id = req_id + 1000
            self.news_subscriptions[hist_req_id] = symbol
            
            self.reqHistoricalNews(
                hist_req_id,
                contract_id,
                provider,
                start_str,
                end_str,
                max_results,
                []
            )
        else:
            print(f"Could not get contract details for {symbol}")



def main():
    app = IBApp()
    try:
        app.connect("127.0.0.1", 4001, 1)
        print("Connecting to IBKR...")
        pump = threading.Thread(target=app.run, daemon=True)
        pump.start()
        
        if not app.ready.wait(timeout=10):
            print("Connection timeout.")
            return

        # Check available providers
        app.reqNewsProviders()
        time.sleep(2)

        print("\n=== OPTION 1: Subscribe to BroadTape (General Market News) ===")
        # Subscribe to BroadTape news feeds (NOT ticker-specific)
        app.subscribe_to_broadtape_news("BRFG")
        time.sleep(1)
        
        print("\n=== OPTION 2: Request Historical News for Specific Tickers ===")
        # Get historical news for specific tickers
        symbols = ["NVDA", "AAPL"]
        for symbol in symbols:
            app.get_historical_news(symbol, days_back=5, max_results=10)
            time.sleep(2)

        print("\nListening for news... Press Ctrl+C to stop")
        while True:
            time.sleep(10)

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        app.disconnect()
        print("Disconnected.")


if __name__ == "__main__":
    main()
