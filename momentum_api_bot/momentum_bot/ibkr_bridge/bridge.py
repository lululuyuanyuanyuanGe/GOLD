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

from ibapi.client import EClient
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
    
    # Fixed request ids for infrequently api calls
    REQ_ID_NEWS_PROVIDERS = -101

    def __init__(self, host: str, port: int, client_id: int, raw_news_queue: Optional[asyncio.Queue] = None):
        self.state = "DISCONNECTED"
        self.host = host
        self.port = port
        self.client_id = client_id
        self.raw_news_queue = raw_news_queue
        
        self.incoming_queue = queue.Queue()
        self.wrapper = IBWrapper(self.incoming_queue)
        self.client = EClient(self.wrapper)
        
        self.api_thread = None
        self.dispatcher_task = None
        self.connection_established_event = asyncio.Event()
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

        self.connection_established_event.clear()

        self._start_api_thread()
        
        self.dispatcher_task = asyncio.create_task(self._dispatch_incoming_messages())

        try:
            # Wait for the event to be set by the dispatcher, with a timeout.
            await asyncio.wait_for(self.connection_established_event.wait(), timeout=10)
            self.state = "OPERATIONAL"
            logging.info("IBKR Bridge is now OPERATIONAL.")
        except asyncio.TimeoutError:
            logging.error("Connection to IBKR timed out. Failed to receive nextValidId.")
            await self.disconnect()
            # self.state is already set to DISCONNECTED by disconnect()
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
        """
        Requests the list of news providers the account is permissioned for.
        """
        logging.info("Requesting news providers...")
        
        req_id = self.REQ_ID_NEWS_PROVIDERS # This is -101
        future = asyncio.get_running_loop().create_future()
        
        # Manually register the future with the correct, fixed ID
        self._pending_requests[req_id] = RequestContext(
            reqId=req_id,
            future=future,
            request_type='NEWS_PROVIDERS'
        )
        
        # Make the direct API call
        self.client.reqNewsProviders()
        
        # Wait for the future to be resolved by the dispatcher
        try:
            # Add a timeout for safety
            response = await asyncio.wait_for(future, timeout=10)
            return response.get('data', {}).get('providers', [])
        except asyncio.TimeoutError:
            logging.error("Request for news providers timed out.")
            # Clean up the pending request to prevent memory leaks
            self._pending_requests.pop(req_id, None)
            return []

    async def subscribe_to_news_feed(self, provider_code: str):
        req_id = self._get_next_req_id()
        contract = Contract()
        
        # For BroadTape news, use the provider:feed format
        contract.symbol = f"{provider_code}:{provider_code}_ALL"  # "BZ:BZ_ALL"
        contract.secType = "NEWS"
        contract.exchange = provider_code  # "BZ" (not empty!)
        
        # Don't use "mdoff,292" for news feeds
        self.client.reqMktData(req_id, contract, "", False, False, [])
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
                if msg_type in ['HISTORICAL_DATA_END', 'ERROR', 'ACCOUNT_SUMMARY_END', 'NEWS_PROVIDERS']:
                    self._handle_response_message(message)
                elif msg_type == 'NEWS_TICK':
                    await self._handle_streaming_message(message)
                else:
                    self._handle_system_message(message)

            except asyncio.CancelledError:
                logging.info("Message dispatcher stopping.")
                break
            except Exception:
                logging.exception("Error in message dispatcher.")

    def _handle_response_message(self, message: dict):
        """
        Handles messages that correspond to a pending request, resolving the
        associated asyncio.Future.
        
        It can find the pending request in two ways:
        1. By `reqId` for most standard requests.
        2. By `request_type` for the few API calls that don't include a `reqId`
           in their response callbacks (e.g., reqNewsProviders).
        """
        msg_type = message['type']
        reqId = message.get('data', {}).get('reqId')

        context = None
        # Find the request context, trying by reqId first, then by type.
        if reqId is not None:
            context = self._pending_requests.get(reqId)
        else:
            # For reqId-less responses, find the first pending request with a matching type.
            for id, ctx in list(self._pending_requests.items()):
                if ctx.request_type == msg_type:
                    context = ctx
                    reqId = id  # Use the internal ID for removal
                    break
        
        if not context:
            logging.debug(f"No pending request found for message: {message}")
            return

        # --- Handle different message types ---

        if msg_type == 'HISTORICAL_DATA_BAR':
            context.data_aggregator.append(message['data']['bar'])
            return  # Don't resolve future yet, wait for HISTORICAL_DATA_END

        elif msg_type == 'HISTORICAL_DATA_END':
            result = {'reqId': reqId, 'data': context.data_aggregator or []}
            if not context.future.done():
                context.future.set_result(result)
        
        elif msg_type == 'NEWS_PROVIDERS':
            if not context.future.done():
                context.future.set_result(message)
                logging.info("Successfully receives all news providers")

        elif msg_type == 'ERROR' and not context.future.done():
            context.future.set_exception(RuntimeError(message['data']['message']))

        else: # Default handler for simple request/response
            if not context.future.done():
                context.future.set_result(message)
        
        # Clean up the pending request
        self._pending_requests.pop(reqId, None)

    async def _handle_streaming_message(self, message: dict):
        if message['type'] == 'NEWS_TICK':
            if self.raw_news_queue:
                await self.raw_news_queue.put(message['data'])

    def _handle_system_message(self, message: dict):
        if message['type'] == 'NEXT_VALID_ID':
            self._set_initial_order_id(message['data']['orderId'])
            
            # Signal that the connection handshake is complete.
            # This will unblock the await in the connect() method.
            self.connection_established_event.set()
        
        elif message['type'] == 'ERROR':
            # --- THIS IS THE FIX ---
            code = message.get('data', {}).get('code')
            message_text = message.get('data', {}).get('message')
            reqId = message.get('data', {}).get('reqId')

            # Differentiate between logging level based on code
            if 2100 <= code <= 2200 or code == 2158:
                logging.info(f"IBKR Info: Code {code}, Message: '{message_text}'")
            else:
                logging.error(f"IBKR Error: reqId {reqId}, Code {code}, Message: '{message_text}'")

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