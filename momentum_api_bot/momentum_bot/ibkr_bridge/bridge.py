import threading
import queue
import time
import logging
import asyncio
from dataclasses import dataclass

from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.tag_value import TagValue

from ibkr_bridge.wrapper import IBWrapper
from ibkr_bridge.client import IBClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


@dataclass
class RequestContext:
    reqId: int
    request_details: dict
    future: asyncio.Future


class IBKRBridge:
    def __init__(self, host='127.0.0.1', port=4002, client_id=1):
        self.host = host
        self.port = port
        self.client_id = client_id

        self.incoming_queue = queue.Queue()  # From IBKR API to asyncio loop
        self.outgoing_queue = queue.Queue()  # From asyncio loop to IBKR API

        self.wrapper = IBWrapper(self.incoming_queue)
        self.client = IBClient(self.wrapper)

        self.api_thread = threading.Thread(target=self._run_api_loop, daemon=True)
        self._is_connected = threading.Event()

        # Here is the request id assignment algorithm
        self._next_req_id = 0
        self._req_id_lock = threading.Lock()
        self._pending_requests = {} # Central registry for pending requests

    def get_next_req_id(self):
        with self._req_id_lock:
            self._next_req_id += 1
            return self._next_req_id
    
    async def fetch_market_data(self, contract: Contract) -> dict:
        """
        Fetches market data for a given contract.
        
        Args:
            contract: The ibapi.contract.Contract object for which to fetch market data.
            
        Returns:
            A dictionary containing the market data.
        """
        req_id = self.get_next_req_id()
        future = asyncio.get_running_loop().create_future()
        context = RequestContext(reqId=req_id, request_details={'type': 'REQ_MKT_DATA', 'contract': contract}, future=future)
        self._pending_requests[req_id] = context
        
        self.outgoing_queue.put({'type': 'REQ_MKT_DATA', 'reqId': req_id, 'contract': contract})
        logging.info(f"Queued market data request for {contract.symbol} with reqId {req_id}")
        return await future

    async def execute_an_order(self, contract: Contract, order: Order) -> dict:
        """
        Places an order for a given contract.
        
        Args:
            contract: The ibapi.contract.Contract object for which to place the order.
            order: The ibapi.order.Order object representing the order details.
            
        Returns:
            A dictionary containing the order status or execution details.
        """
        req_id = self.get_next_req_id()
        future = asyncio.get_running_loop().create_future()
        context = RequestContext(reqId=req_id, request_details={'type': 'PLACE_ORDER', 'contract': contract, 'order': order}, future=future)
        self._pending_requests[req_id] = context
        
        self.outgoing_queue.put({'type': 'PLACE_ORDER', 'reqId': req_id, 'contract': contract, 'order': order})
        logging.info(f"Queued order placement for {contract.symbol} with reqId {req_id}")
        return await future

    async def subscribe_news_provider(self, provider_code: str, article_id: str) -> dict:
        """
        Subscribes to a news provider or requests a specific news article.
        
        Args:
            provider_code: The code of the news provider (e.g., 'BZ').
            article_id: The ID of the news article to request.
            
        Returns:
            A dictionary containing the news article content.
        """
        req_id = self.get_next_req_id()
        future = asyncio.get_running_loop().create_future()
        context = RequestContext(reqId=req_id, request_details={'type': 'REQ_NEWS_ARTICLE', 'providerCode': provider_code, 'articleId': article_id}, future=future)
        self._pending_requests[req_id] = context
        
        self.outgoing_queue.put({'type': 'REQ_NEWS_ARTICLE', 'reqId': req_id, 'providerCode': provider_code, 'articleId': article_id})
        logging.info(f"Queued news article request for {article_id} from {provider_code} with reqId {req_id}")
        return await future

    async def check_account_info(self, group: str = 'All', tags: str = 'AccountType,NetLiquidation,TotalCashValue,SettledCash,AccruedCash,BuyingPower,EquityWithLoanValue,PreviousDayEquityWithLoanValue,GrossPositionValue,MaintenanceMargin,InitMargin,AvailableFunds,UnrealizedPnL,RealizedPnL,DayTradesRemaining,Leverage') -> dict:
        """
        Checks the account information, including positions, balance, etc.
        
        Args:
            group: The account summary group (e.g., 'All', 'Cash').
            tags: A comma-separated string of tags for the account summary.
            
        Returns:
            A dictionary containing the account information.
        """
        req_id = self.get_next_req_id()
        future = asyncio.get_running_loop().create_future()
        context = RequestContext(reqId=req_id, request_details={'type': 'REQ_ACCOUNT_SUMMARY', 'group': group, 'tags': tags}, future=future)
        self._pending_requests[req_id] = context
        
        self.outgoing_queue.put({'type': 'REQ_ACCOUNT_SUMMARY', 'reqId': req_id, 'group': group, 'tags': tags})
        logging.info(f"Queued account summary request with reqId {req_id}")
        return await future

    def _run_api_loop(self):
        logging.info("Starting IBKR API thread...")
        self.client.connect(self.host, self.port, self.client_id)
        if self.client.isConnected():
            self._is_connected.set()
            logging.info("IBKR API client connected.")
        self.client.run()
        logging.info("IBKR API thread stopped.")

    async def _process_incoming_messages(self):
        """
        Asynchronously processes messages from the incoming_queue (from IBKR API thread).
        Dispatches responses to the appropriate asyncio.Future objects.
        """
        while True:
            try:
                # Use a non-blocking get with a timeout to allow for graceful shutdown
                message = await asyncio.to_thread(self.incoming_queue.get, timeout=1)
                req_id = message.get('reqId')
                if req_id in self._pending_requests:
                    context = self._pending_requests.pop(req_id)
                    if not context.future.done():
                        context.future.set_result(message)
                else:
                    logging.warning(f"Received unsolicited message or reqId not found: {message}")
                self.incoming_queue.task_done()
            except queue.Empty:
                await asyncio.sleep(0.1)  # Briefly sleep if queue is empty to prevent busy-waiting
            except Exception as e:
                logging.error(f"Error processing incoming message: {e}")

    async def _process_outgoing_requests(self):
        """
        Asynchronously processes requests from the outgoing_queue (to IBKR API thread).
        Calls the appropriate EClient methods based on the request type.
        """
        while True:
            try:
                request = await asyncio.to_thread(self.outgoing_queue.get, timeout=1)
                req_id = request.get('reqId')
                request_type = request.get('type')
                
                if request_type == 'REQ_MKT_DATA':
                    contract = request.get('contract')
                    # Assuming reqMktData takes a Contract object and a generic_tick_list string
                    self.client.reqMktData(reqId=req_id, contract=contract, genericTickList="", snapshot=False, regulatorySnaphsot=False, mktDataOptions=[])
                    logging.info(f"Requested market data for {contract.symbol} with reqId {req_id}")
                elif request_type == 'PLACE_ORDER':
                    contract = request.get('contract')
                    order = request.get('order')
                    self.client.placeOrder(reqId=req_id, contract=contract, order=order)
                    logging.info(f"Placed order for {contract.symbol} with reqId {req_id}")
                elif request_type == 'REQ_NEWS_ARTICLE':
                    article_id = request.get('articleId')
                    provider_code = request.get('providerCode')
                    self.client.reqNewsArticle(reqId=req_id, providerCode=provider_code, articleId=article_id, newsArticleOptions=[])
                    logging.info(f"Requested news article {article_id} from {provider_code} with reqId {req_id}")
                elif request_type == 'REQ_ACCOUNT_SUMMARY':
                    group = request.get('group', 'All')
                    tags = request.get('tags', 'AccountType,NetLiquidation,TotalCashValue,SettledCash,AccruedCash,BuyingPower,EquityWithLoanValue,PreviousDayEquityWithLoanValue,GrossPositionValue,MaintenanceMargin,InitMargin,AvailableFunds,UnrealizedPnL,RealizedPnL,DayTradesRemaining,Leverage')
                    self.client.reqAccountSummary(reqId=req_id, groupName=group, tags=tags)
                    logging.info(f"Requested account summary with reqId {req_id}")
                else:
                    logging.warning(f"Unknown request type: {request_type} for reqId {req_id}")
                self.outgoing_queue.task_done()
            except queue.Empty:
                await asyncio.sleep(0.1)
            except Exception as e:
                logging.error(f"Error processing outgoing request: {e}")


    async def start(self):
        """
        Starts the IBKR API thread and waits for the connection to be established.
        Also initiates the asynchronous processing of incoming and outgoing messages.
        """
        logging.info("Starting IBKRBridge...")
        self.api_thread.start()
        logging.info("Waiting for IBKR API client to connect...")
        self._is_connected.wait()  # Wait until the API client is connected
        logging.info("IBKR API client connected. Starting message processing tasks.")
        
        # Start the asynchronous tasks for processing queues
        asyncio.create_task(self._process_incoming_messages())
        asyncio.create_task(self._process_outgoing_requests())


   