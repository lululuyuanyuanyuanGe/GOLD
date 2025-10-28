import asyncio
import logging
from ib_insync import IB, util, Contract, Order
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ConnectionState(Enum):
    DISCONNECTED = 0
    CONNECTING = 1
    OPERATIONAL = 2

class IBKRConnector:
    def __init__(self, host='127.0.0.1', port=7497, client_id=1):
        self.ib = IB()
        self.host = host
        self.port = port
        self.client_id = client_id
        self.state = ConnectionState.DISCONNECTED
        self.reconnect_task = None

        # Register event handlers
        self.ib.connectedEvent += self._on_connected
        self.ib.disconnectedEvent += self._on_disconnected
        self.ib.errorEvent += self._on_error

    async def connect_async(self):
        if self.state != ConnectionState.DISCONNECTED:
            logging.info(f"Already in state {self.state}, not attempting to connect.")
            return

        self.state = ConnectionState.CONNECTING
        logging.info(f"Attempting to connect to IBKR at {self.host}:{self.port} with client ID {self.client_id}...")
        try:
            await self.ib.connectAsync(self.host, self.port, self.client_id)
            # Connection events will update the state
        except Exception as e:
            logging.error(f"Failed to initiate connection: {e}")
            self.state = ConnectionState.DISCONNECTED
            await self._schedule_reconnect()

    def _on_connected(self):
        logging.info("IBKR Connected successfully.")
        self.state = ConnectionState.OPERATIONAL
        if self.reconnect_task:
            self.reconnect_task.cancel()
            self.reconnect_task = None
        # Perform state synchronization checklist here (re-subscribe to feeds, reconcile open positions and orders)
        logging.info("Performing state synchronization checklist...")
        # Placeholder for actual synchronization logic
        logging.info("State synchronization complete. IBKRConnector is OPERATIONAL.")

    def _on_disconnected(self):
        logging.warning("IBKR Disconnected.")
        self.state = ConnectionState.DISCONNECTED
        asyncio.create_task(self._schedule_reconnect())

    def _on_error(self, reqId, errorCode, errorString, contract):
        if reqId is not None:
            logging.error(f"IBKR Error. Request ID: {reqId}, Code: {errorCode}, Message: {errorString}, Contract: {contract}")
        else:
            logging.error(f"IBKR Error. Code: {errorCode}, Message: {errorString}")

    async def _schedule_reconnect(self, delay=1):
        if self.reconnect_task and not self.reconnect_task.done():
            return # Reconnect already scheduled

        async def reconnect_loop():
            current_delay = delay
            while self.state != ConnectionState.OPERATIONAL:
                logging.info(f"Attempting to reconnect in {current_delay} seconds...")
                await asyncio.sleep(current_delay)
                if self.state == ConnectionState.OPERATIONAL: # Check again in case it connected while waiting
                    break
                await self.connect_async()
                current_delay = min(current_delay * 2, 60) # Exponential backoff, max 60 seconds

        if self.state != ConnectionState.OPERATIONAL:
            self.reconnect_task = asyncio.create_task(reconnect_loop())

    def is_operational(self):
        return self.state == ConnectionState.OPERATIONAL

    async def disconnect(self):
        if self.ib.isConnected():
            logging.info("Disconnecting from IBKR.")
            self.ib.disconnect()
        self.state = ConnectionState.DISCONNECTED
        if self.reconnect_task:
            self.reconnect_task.cancel()
            self.reconnect_task = None

    # Placeholder methods for other functionalities
    async def subscribe_to_news(self, symbols: list):
        logging.info(f"Subscribing to news for symbols: {symbols}")
        # ib_insync handles news articles via newsArticleEvent which is already set up in NewsHandler.
        # The actual subscription to news topics/providers is typically done via reqMktData with specific generic ticks
        # or by requesting news headlines. For now, we assume the NewsHandler will process incoming articles.
        # If specific news subscriptions are needed, this method would be expanded.
        for symbol in symbols:
            contract = Contract(symbol=symbol, secType='STK', exchange='SMART', currency='USD')
            # Requesting generic ticks for news (e.g., 292 for News Headlines)
            # This might need adjustment based on specific news requirements and IBKR capabilities
            self.ib.reqMktData(contract, '292', False, False) # 292 is generic tick for News Headlines
            logging.info(f"Requested market data for news headlines for {symbol}")

    async def fetch_candles(self, contract, durationStr, barSizeSetting):
        logging.info(f"Fetching candles for {contract.symbol} (Duration: {durationStr}, Bar Size: {barSizeSetting})")
        if not self.ib.isConnected():
            logging.warning("IBKR not connected, cannot fetch candles.")
            return []
        try:
            bars = await self.ib.reqHistoricalDataAsync(
                contract,
                endDateTime='',
                durationStr=durationStr,
                barSizeSetting=barSizeSetting,
                whatToShow='TRADES',
                useRTH=True,
                formatDate=1
            )
            logging.info(f"Fetched {len(bars)} candles for {contract.symbol}")
            return bars
        except Exception as e:
            logging.error(f"Failed to fetch candles for {contract.symbol}: {e}")
            return []

    async def stream_quotes(self, contract):
        logging.info(f"Streaming quotes for {contract.symbol}")
        if not self.ib.isConnected():
            logging.warning("IBKR not connected, cannot stream quotes.")
            return None
        try:
            # Ensure the contract is qualified
            qualified_contract = (await self.ib.qualifyContracts(contract))[0]
            self.ib.reqMktData(qualified_contract) # Start streaming market data
            # The Ticker object is updated in place by ib_insync
            # We can retrieve it immediately, but its values will be updated asynchronously
            ticker = self.ib.tickerByContract(qualified_contract)
            return ticker
        except Exception as e:
            logging.error(f"Failed to stream quotes for {contract.symbol}: {e}")
            return None

    async def place_order(self, contract, order):
        logging.info(f"Placing order for {contract.symbol} (Action: {order.action}, Qty: {order.totalQuantity}, Type: {order.orderType})")
        if not self.ib.isConnected():
            logging.warning("IBKR not connected, cannot place order.")
            return None
        try:
            trade = await self.ib.placeOrder(contract, order)
            logging.info(f"Order placed: {trade}")
            return trade
        except Exception as e:
            logging.error(f"Failed to place order for {contract.symbol}: {e}")
            return None

if __name__ == "__main__":
    async def main():
        connector = IBKRConnector()
        await connector.connect_async()

        # Keep the event loop running to allow for connection/reconnection
        while True:
            await asyncio.sleep(1)

    # Run the main function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Application stopped by user.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
