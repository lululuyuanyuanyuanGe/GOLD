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
        self.news_subscriptions = {}  # Track active subscriptions
        self.company_news = {}  # Store news by symbol
        self.contract_details = {}  # Store contract details

    def nextValidId(self, orderId):
        print("Connected with nextValidId:", orderId)
        self.ready.set()

    def newsProviders(self, newsProviders):
        print(f"Got {len(newsProviders)} news providers:")
        for p in newsProviders:
            print(f"  {p.code}: {p.name}")

    def tickNews(self, tickerId, timeStamp, providerCode, articleId, headline, extraData):
        """Real-time news for specific symbols"""
        news_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timeStamp))
        
        # Find which symbol this news is for
        symbol = self.news_subscriptions.get(tickerId, "Unknown")
        
        print(f"📰 [{news_time}] {symbol} ({providerCode}): {headline}")
        
        # Store news for this symbol
        if symbol not in self.company_news:
            self.company_news[symbol] = []
        
        self.company_news[symbol].append({
            'timestamp': timeStamp,
            'time_str': news_time,
            'provider': providerCode,
            'headline': headline,
            'article_id': articleId,
            'extra_data': extraData
        })
        
        # Optionally fetch full article
        if "earnings" in headline.lower() or "guidance" in headline.lower():
            print(f"🔍 Fetching full article for: {headline[:50]}...")
            self.reqNewsArticle(1000 + tickerId, providerCode, articleId, [])

    def historicalNews(self, requestId, time, providerCode, articleId, headline):
        """Historical news callback"""
        symbol = self.news_subscriptions.get(requestId, "Historical")
        print(f"📚 [{time}] {symbol} (Historical): {headline}")
        
        # Store historical news
        if symbol not in self.company_news:
            self.company_news[symbol] = []
            
        self.company_news[symbol].append({
            'timestamp': time,
            'time_str': time,
            'provider': providerCode,
            'headline': headline,
            'article_id': articleId,
            'type': 'historical'
        })

    def newsArticle(self, requestId, articleType, articleText):
        """Full article content"""
        print(f"📄 Full article (ID {requestId}): {len(articleText)} characters")

    def contractDetails(self, reqId, contractDetails):
        """Store contract details for news requests"""
        self.contract_details[reqId] = contractDetails.contract

    def contractDetailsEnd(self, reqId):
        """Called when contract details are complete"""
        pass

    def error(self, reqId, code, msg, advancedOrderReject=""):
        if code not in [2104, 2106, 2107, 2157]:
            print(f"Error {code}: {msg}")

    # NEW METHODS FOR COMPANY-SPECIFIC NEWS
    
    def subscribe_to_company_news(self, symbol, exchange="SMART", currency="USD"):
        """Subscribe to real-time news for a specific company"""
        print(f"🔔 Subscribing to real-time news for {symbol}...")
        
        # Create stock contract
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.exchange = exchange
        contract.currency = currency
        
        # Use a unique request ID
        req_id = len(self.news_subscriptions) + 10
        self.news_subscriptions[req_id] = symbol
        
        # Subscribe with generic tick 292 for news
        self.reqMktData(req_id, contract, "mdoff,292", False, False, [])
        
        return req_id

    def get_historical_news(self, symbol, days_back=7, max_results=50):
        """Get historical news for a specific company"""
        print(f"📚 Requesting {days_back} days of historical news for {symbol}...")
        
        # First get contract details to get the contract ID
        req_id = len(self.news_subscriptions) + 100
        self.news_subscriptions[req_id] = symbol
        
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"
        
        # Get contract details first
        self.reqContractDetails(req_id, contract)
        
        # Wait a bit for contract details
        time.sleep(2)
        
        if req_id in self.contract_details:
            contract_id = self.contract_details[req_id].conId
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Format dates for IBKR
            start_str = start_date.strftime("%Y%m%d-%H:%M:%S")
            end_str = end_date.strftime("%Y%m%d-%H:%M:%S")
            
            # Request historical news
            self.reqHistoricalNews(
                req_id + 1000,
                contract_id,
                "BRFG",  # Only free provider
                start_str,
                end_str,
                max_results,
                []
            )
        else:
            print(f"❌ Could not get contract details for {symbol}")

    def get_company_news_summary(self, symbol):
        """Get summary of news for a company"""
        if symbol in self.company_news:
            news_list = self.company_news[symbol]
            print(f"\n📊 News Summary for {symbol} ({len(news_list)} articles):")
            print("=" * 60)
            
            for i, news in enumerate(news_list[-10:], 1):  # Show last 10
                print(f"{i:2d}. [{news['time_str']}] {news['headline'][:80]}...")
                
            return news_list
        else:
            print(f"No news found for {symbol}")
            return []

def main():
    app = IBApp()

    # Connect and start message pump
    app.connect("127.0.0.1", 4001, 1)
    pump = threading.Thread(target=app.run, daemon=False)
    pump.start()

    # Wait for connection
    if not app.ready.wait(timeout=10):
        print("Connection timeout")
        return

    # Get news providers first
    app.reqNewsProviders()
    time.sleep(2)

    # Subscribe to company-specific news
    symbols = ["AAPL", "TSLA", "NVDA"]
    
    for symbol in symbols:
        # Real-time news subscription
        app.subscribe_to_company_news(symbol)
        time.sleep(1)
        
        # Historical news (last 3 days)
        app.get_historical_news(symbol, days_back=30, max_results=20)
        time.sleep(1)

    # Listen for news
    print("\n🎧 Listening for company-specific news... Press Ctrl+C to stop")
    
    try:
        # Wait and periodically show summaries
        for i in range(6):  # Run for 30 seconds
            time.sleep(5)
            
            # Show news summary every 5 seconds
            for symbol in symbols:
                if symbol in app.company_news:
                    count = len(app.company_news[symbol])
                    if count > 0:
                        print(f"📈 {symbol}: {count} news articles collected")
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping news listener...")
        
        # Show final summaries
        for symbol in symbols:
            app.get_company_news_summary(symbol)

    # Cleanup
    app.disconnect()
    pump.join(timeout=2)

if __name__ == "__main__":
    main()
