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
        self.contract_details = {}
        self.historical_news_complete = {}

    def nextValidId(self, orderId):
        print(f"Connection successful. Next valid ID: {orderId}")
        self.ready.set()

    def newsProviders(self, newsProviders):
        provider_codes = [p.code for p in newsProviders]
        print(f"Available news providers: {provider_codes}\n")

    def tickNews(self, tickerId, timeStamp, providerCode, articleId, headline, extraData):
        """Real-time BroadTape news callback"""
        news_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timeStamp))
        feed = self.news_subscriptions.get(tickerId, "Unknown")
        
        # Clean metadata from headline
        clean_headline = headline.split('!')[-1] if '!' in headline else headline
        
        print(f"\n--- REAL-TIME BROADTAPE NEWS ---")
        print(f"  Feed: {feed}")
        print(f"  Time: {news_time}")
        print(f"  Provider: {providerCode}")
        print(f"  Headline: {clean_headline}")
        print("--------------------------------")

    def historicalNews(self, requestId, time, providerCode, articleId, headline):
        """Historical news callback"""
        feed = self.news_subscriptions.get(requestId, "Historical")
        
        # Clean metadata from headline
        clean_headline = headline.split('!')[-1] if '!' in headline else headline
        
        print(f"\n--- HISTORICAL BROADTAPE NEWS ---")
        print(f"  Feed: {feed}")
        print(f"  Time: {time}")
        print(f"  Provider: {providerCode}")
        print(f"  Headline: {clean_headline}")
        print("---------------------------------")

    def historicalNewsEnd(self, requestId, hasMore):
        """Called when historical news request is complete"""
        feed = self.news_subscriptions.get(requestId, "Historical")
        print(f"\n=== Historical news complete for {feed} (hasMore: {hasMore}) ===\n")
        self.historical_news_complete[requestId] = True

    def contractDetails(self, reqId, contractDetails):
        print(f"Received contract details for request {reqId}")
        self.contract_details[reqId] = contractDetails.contract

    def contractDetailsEnd(self, reqId):
        print(f"Finished receiving contract details for request {reqId}")

    def error(self, reqId, code, msg, advancedOrderReject=""):
        # Filter out informational messages
        if code in [2104, 2107, 2157, 2106, 2158]:
            return
        print(f"ERROR {code} (ReqID {reqId}): {msg}")

    def subscribe_to_broadtape(self, provider_code):
        """Subscribe to real-time BroadTape general market news"""
        print(f"Subscribing to {provider_code} real-time BroadTape...")
        
        contract = Contract()
        contract.symbol = f"{provider_code}:{provider_code}_ALL"
        contract.secType = "NEWS"
        contract.exchange = provider_code
        
        req_id = 9000 + len(self.news_subscriptions)
        self.news_subscriptions[req_id] = f"{provider_code}_BroadTape_RealTime"
        
        self.reqMktData(req_id, contract, "", False, False, [])
        return req_id

    def get_broadtape_historical_news(self, provider_code, days_back=5, max_results=100):
        """Get historical BroadTape news (general market, not ticker-specific)"""
        print(f"Requesting {days_back} days of historical BroadTape news from {provider_code}...")
        
        # For BroadTape historical news, we need to get the NEWS contract details first
        contract = Contract()
        contract.symbol = f"{provider_code}:{provider_code}_ALL"
        contract.secType = "NEWS"
        contract.exchange = provider_code
        
        req_id = 8000 + len(self.contract_details)
        self.reqContractDetails(req_id, contract)
        
        print(f"Waiting for NEWS contract details for {provider_code}...")
        time.sleep(3)
        
        if req_id in self.contract_details:
            contract_id = self.contract_details[req_id].conId
            print(f"Contract ID for {provider_code} BroadTape: {contract_id}")
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # CRITICAL: Use space, not hyphen
            start_str = start_date.strftime("%Y%m%d %H:%M:%S")
            end_str = end_date.strftime("%Y%m%d %H:%M:%S")
            
            print(f"Requesting BroadTape news from {start_str} to {end_str}")
            
            hist_req_id = req_id + 1000
            self.news_subscriptions[hist_req_id] = f"{provider_code}_BroadTape_Historical"
            
            self.reqHistoricalNews(
                hist_req_id,
                contract_id,
                provider_code,
                start_str,
                end_str,
                max_results,
                []
            )
        else:
            print(f"Could not get contract details for {provider_code} BroadTape")


def main():
    app = IBApp()
    try:
        app.connect("127.0.0.1", 4001, 1)
        print("Connecting to IBKR Gateway...")
        
        pump = threading.Thread(target=app.run, daemon=True)
        pump.start()
        
        if not app.ready.wait(timeout=10):
            print("Connection timeout.")
            return

        # Check available providers
        app.reqNewsProviders()
        time.sleep(2)

        print("=" * 60)
        print("PART 1: HISTORICAL BROADTAPE NEWS (Last 5 Days)")
        print("=" * 60 + "\n")
        
        # Get 5 days of historical BroadTape news
        providers_for_historical = ["BRFG", "DJNL"]
        
        for provider in providers_for_historical:
            app.get_broadtape_historical_news(provider, days_back=5, max_results=50)
            time.sleep(3)  # Wait for historical news to arrive
        
        # Wait for all historical news to complete
        print("\nWaiting for all historical news to complete...")
        time.sleep(5)
        
        print("\n" + "=" * 60)
        print("PART 2: REAL-TIME BROADTAPE NEWS STREAMING")
        print("=" * 60 + "\n")
        
        # Subscribe to real-time BroadTape feeds
        app.subscribe_to_broadtape("BRFG")   # Briefing.com general market
        time.sleep(1)
        app.subscribe_to_broadtape("DJNL")   # Dow Jones newsletters
        time.sleep(1)
        
        print("\nListening for real-time BroadTape news...")
        print("NOTE: Real-time news only flows during market hours (Mon-Fri)")
        print("Press Ctrl+C to stop\n")
        
        while True:
            time.sleep(10)

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        app.disconnect()
        print("Disconnected.")


if __name__ == "__main__":
    main()
