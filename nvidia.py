import re
import threading
import time
from datetime import datetime, timedelta
from ibapi.client import EClient
from ibapi.contract import Contract, ContractDetails
from ibapi.wrapper import EWrapper

# Extend IBKR API base class
class IBapi(EClient, EWrapper):
    def __init__(self):
        EClient.__init__(self, self)
        self.conId = None
    
    def contractDetails(self, reqId: int, contractDetails: ContractDetails):
        """Store contract ID for the ticker"""
        self.conId = contractDetails.contract.conId
        print(f"Contract ID for NVDA: {self.conId}")
    
    def historicalNews(self, requestId, timeStamp, providerCode, articleId, headline):
        """Receive and display news headlines"""
        clean_headline = re.sub(r"\{.*?\}!?", "", headline)  # Remove metadata
        print(f"{timeStamp} {clean_headline}")
    
    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        """Handle errors"""
        print(f"Error {errorCode}: {errorString}")

# Connection settings
TWS_HOST = "127.0.0.1"
TWS_PORT = 4002  # 4002 for paper trading, 4001 for live
CLIENT_ID = 1

# Initialize and connect
app = IBapi()
app.connect(TWS_HOST, TWS_PORT, CLIENT_ID)
threading.Thread(target=app.run, daemon=True).start()
time.sleep(2)  # Allow connection to establish

# Define NVIDIA contract
contract = Contract()
contract.symbol = "NVDA"
contract.secType = "STK"
contract.exchange = "SMART"
contract.currency = "USD"

# Get contract details to retrieve conId
app.reqContractDetails(reqId=101, contract=contract)
time.sleep(2)  # Wait for contract details

# Request historical news (last 10 days, 15 results max)
PROVIDERS = "BRFG+BRFUPDN+DJNL"  # Three free news sources
end_date = datetime.now().strftime("%Y%m%d %H:%M:%S")
start_date = (datetime.now() - timedelta(days=10)).strftime("%Y%m%d %H:%M:%S")

app.reqHistoricalNews(
    reqId=102,
    conId=app.conId,
    providerCodes=PROVIDERS,
    startDateTime=start_date,
    endDateTime=end_date,
    totalResults=15,
    historicalNewsOptions=[]
)

time.sleep(3)  # Wait for news to arrive
app.disconnect()
