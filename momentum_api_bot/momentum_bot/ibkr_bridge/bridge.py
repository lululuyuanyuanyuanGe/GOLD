"""
Contains the IBKRBridge class, the central orchestrator for all communication
with the Interactive Brokers API.

This class is responsible for:
1.  Managing the dedicated thread for the synchronous official 'ibapi'.
2.  Instantiating and connecting the IBClient and IBWrapper.
3.  Managing the thread-safe queue for receiving messages.
4.  Providing a high-level, asynchronous interface for the rest of the application.
5.  Managing the request/response lifecycle using unique IDs and asyncio.Future objects.
6.  Handling the connection state machine (Disconnected, Connecting, Operational).
7.  Managing the generation of unique, thread-safe order IDs and request IDs.
"""

import asyncio
import queue
import threading
import logging
from dataclasses import dataclass, field
from typing import Optional, Callable, Coroutine, Any, List

from .client import IBClient
from .wrapper import IBWrapper
from ibapi.contract import Contract
from ibapi.order import Order

# --- Data model for the request registry ---
@dataclass
class RequestContext:
    """Holds the context for a single pending request."""
    reqId: int
    future: asyncio.Future
    request_type: str  # The type of the original request, e.g., 'REQ_NEWS_PROVIDERS'
    data_aggregator: List = field(default_factory=list) # For multi-part responses

class IBKRBridge:
    """
    The main bridge between the asynchronous application logic and the
    synchronous, threaded IBKR API client.
    """

    def __init__(self, host: str, port: int, client_id: int):
        self.state = "DISCONNECTED"
        self.host = host
        self.port = port
        self.client_id = client_id
        
        self.news_handler_callback: Optional[Callable[[str], Coroutine[Any, Any, None]]] = None

        self.incoming_queue = queue.Queue()
        self.wrapper = IBWrapper(self.incoming_queue)
        self.client = IBClient(self.wrapper)
        
        self.api_thread = None
        self.dispatcher_task = None
        self._pending_requests = {}
        
        self._next_req_id = 0
        self._req_id_lock = threading.Lock()
        self._next_order_id = -1
        self._order_id_lock = threading.Lock()

    # --- Public High-Level Async Methods (The Application Interface) ---

    async def connect(self):
        if self.state != "DISCONNECTED":
            logging.warning("Bridge is already connected or connecting.")
            return

        logging.info(f"Connecting to IBKR at {self.host}:{self.port}...")
        self.state = "CONNECTING"
        self._start_api_thread()
        
        connection_future = asyncio.get_running_loop().create_future()
        self._pending_requests['connection'] = RequestContext(reqId=-1, future=connection_future, request_type='CONNECTION')

        self.dispatcher_task = asyncio.create_task(self._dispatch_incoming_messages())

        try:
            await asyncio.wait_for(connection_future, timeout=10)
            self.state = "OPERATIONAL"
            logging.info("IBKR Bridge is now OPERATIONAL.")
        except asyncio.TimeoutError:
            logging.error("Connection to IBKR timed out. Failed to receive nextValidId.")
            await self.disconnect()
            self.state = "DISCONNECTED"
            raise ConnectionError("IBKR connection timed out.")

    async def disconnect(self):
        if self.state == "DISCONNECTED":
            return
            
        logging.info("Disconnecting from IBKR...")
        self.state = "DISCONNECTED"

        if self.dispatcher_task:
            self.dispatcher_task.cancel()
        
        # This signals the client.run() loop in the API thread to exit
        self.client.disconnect()
        
        if self.api_thread and self.api_thread.is_alive():
            self.api_thread.join(timeout=5)
        
        logging.info("IBKR Bridge disconnected.")

    async def request_news_providers(self) -> list:
        logging.info("Requesting news providers...")
        # This request type's callback doesn't have a reqId, so we handle it specially
        future = await self._send_request('REQ_NEWS_PROVIDERS', use_req_id=False)
        self.client.reqNewsProviders() # Make the direct API call
        response = await future
        return response.get('data', {}).get('providers', [])

    async def subscribe_to_news_feed(self, provider_code: str):
        req_id = self._get_next_req_id()
        contract = Contract()
        contract.secType = "NEWS"
        contract.exchange = provider_code
        
        self.client.reqMktData(req_id, contract, "292", False, False, [])
        logging.info(f"Sent subscription request for news provider: {provider_code} with reqId {req_id}")

    async def fetch_historical_data(self, contract: Contract, duration: str, bar_size: str) -> list:
        logging.info(f"Requesting historical data for {contract.symbol}...")
        future = await self._send_request(
            'REQ_HISTORICAL_DATA',
            contract=contract,
            durationStr=duration,
            barSizeSetting=bar_size,
            whatToShow='TRADES',
            useRTH=1,
            formatDate=1,
            keepUpToDate=False
        )
        # The EClient method is called inside _send_request for this pattern
        response = await future
        return response.get('data', [])

    async def place_order(self, contract: Contract, order: Order) -> int:
        order_id = self._get_next_order_id()
        order.orderId = order_id
        
        self.client.placeOrder(order_id, contract, order)
        logging.info(f"Sent request to place order {order_id} for {contract.symbol}")
        return order_id
    
    # --- Internal Core Logic Methods ---

    def _start_api_thread(self):
        """
        Connects the client and starts the dedicated thread for the EClient's
        internal message processing loop.
        """
        self.client.connect(self.host, self.port, self.client_id)
        self.api_thread = threading.Thread(target=self.client.run, daemon=True)
        self.api_thread.start()
        logging.info("IBKR API thread started, running the internal message loop.")

    async def _dispatch_incoming_messages(self):
        logging.info("Async message dispatcher started.")
        while self.state != "DISCONNECTED":
            try:
                message = await asyncio.to_thread(self.incoming_queue.get)
                logging.debug(f"Dispatcher received message: {message['type']}")
                
                msg_type = message.get('type')
                if msg_type in ['HISTORICAL_DATA_END', 'ERROR', 'ACCOUNT_SUMMARY_END']:
                    self._handle_response_message(message)
                elif msg_type == 'NEWS_PROVIDERS': # Special handling for reqId-less responses
                    self._handle_reqid_less_response(message)
                elif msg_type == 'NEWS_TICK':
                    self._handle_streaming_message(message)
                else:
                    self._handle_system_message(message)

            except asyncio.CancelledError:
                logging.info("Message dispatcher stopping.")
                break
            except Exception:
                logging.exception("Error in message dispatcher.")

    def _handle_reqid_less_response(self, message: dict):
        """Handles responses that don't have a reqId in their callback."""
        msg_type = message['type']
        for reqId, context in list(self._pending_requests.items()):
            if context.request_type == msg_type:
                if not context.future.done():
                    context.future.set_result(message)
                    self._pending_requests.pop(reqId)
                return

    def _handle_response_message(self, message: dict):
        reqId = message.get('data', {}).get('reqId')
        context = self._pending_requests.get(reqId)
        if not context:
            return

        if message['type'] == 'HISTORICAL_DATA_BAR':
            context.data_aggregator.append(message['data']['bar'])
        
        elif message['type'] == 'HISTORICAL_DATA_END':
            result = {'reqId': reqId, 'data': context.data_aggregator or []}
            if not context.future.done():
                context.future.set_result(result)
            self._pending_requests.pop(reqId, None)

        elif message['type'] == 'ERROR' and not context.future.done():
            context.future.set_exception(RuntimeError(message['data']['message']))
            self._pending_requests.pop(reqId, None)

        else:
            if not context.future.done():
                context.future.set_result(message)
                self._pending_requests.pop(reqId, None)

    def _handle_streaming_message(self, message: dict):
        if message['type'] == 'NEWS_TICK':
            if self.news_handler_callback and asyncio.iscoroutinefunction(self.news_handler_callback):
                asyncio.create_task(self.news_handler_callback(message['data']['article']))

    def _handle_system_message(self, message: dict):
        if message['type'] == 'NEXT_VALID_ID':
            self._set_initial_order_id(message['data']['orderId'])
            if 'connection' in self._pending_requests:
                context = self._pending_requests.pop('connection')
                if not context.future.done():
                    context.future.set_result(True)
        
        elif message['type'] == 'ERROR':
            logging.error(f"IBKR Error. Request ID: {message['data']['reqId']}, Code: {message['data']['code']}, Message: {message['data']['message']}")

    async def _send_request(self, request_type: str, use_req_id: bool = True, **kwargs) -> asyncio.Future:
        req_id = self._get_next_req_id() if use_req_id else -1
        future = asyncio.get_running_loop().create_future()
        
        # The key for reqId-less requests will be its temporary reqId (-1, -2, etc.)
        self._pending_requests[req_id] = RequestContext(reqId=req_id, future=future, request_type=request_type)
        
        # For methods that fit the pattern, we can call the client here
        if hasattr(self.client, request_type.lower()):
            method_to_call = getattr(self.client, request_type.lower())
            method_to_call(req_id, **kwargs)
        
        return future

    # --- ID Generation Methods --- (These are unchanged and correct)
    def _get_next_req_id(self) -> int:
        with self._req_id_lock:
            self._next_req_id += 1
            return self._next_req_id

    def _get_next_order_id(self) -> int:
        with self._order_id_lock:
            if self._next_order_id == -1:
                raise ConnectionError("Cannot get next order ID: nextValidId has not been received from IBKR yet.")
            current_id = self._next_order_id
            self._next_order_id += 1
            return current_id
    
    def _set_initial_order_id(self, order_id: int):
        with self._order_id_lock:
            if self._next_order_id == -1:
                self._next_order_id = order_id
                logging.info(f"Initial order ID set to: {order_id}")