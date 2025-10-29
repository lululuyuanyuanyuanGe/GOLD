"""
Contains the IBKRBridge class, the central orchestrator for all communication
with the Interactive Brokers API.

This class is responsible for:
1.  Managing the dedicated thread for the synchronous official 'ibapi'.
2.  Instantiating and connecting the IBClient and IBWrapper.
3.  Managing the thread-safe queues for sending and receiving messages.
4.  Providing a high-level, asynchronous interface for the rest of the application.
5.  Managing the request/response lifecycle using unique IDs and asyncio.Future objects.
6.  Handling the connection state machine (Disconnected, Connecting, Operational).
7.  Managing the generation of unique, thread-safe order IDs and request IDs.
"""

import asyncio
import queue
import threading
import logging
from dataclasses import dataclass
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
    data_aggregator: list = [] # For multi-part responses like historical data

class IBKRBridge:
    """
    The main bridge between the asynchronous application logic and the
    synchronous, threaded IBKR API client.
    """

    def __init__(self, host: str, port: int, client_id: int):
        """
        Initializes the bridge, but does not connect.

        Args:
            host: The IP address of the TWS/Gateway.
            port: The port number of the TWS/Gateway.
            client_id: The client ID for this API session.
        """
        self.state = "DISCONNECTED"
        self.host = host
        self.port = port
        self.client_id = client_id
        
        self.news_handler_callback = None # To be set by the news service

        self.incoming_queue = queue.Queue()
        self.outgoing_queue = queue.Queue()

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
        """
        Connects to the IBKR Gateway and starts all processing loops.
        """
        if self.state != "DISCONNECTED":
            logging.warning("Bridge is already connected or connecting.")
            return

        logging.info(f"Connecting to IBKR at {self.host}:{self.port}...")
        self.state = "CONNECTING"
        self._start_api_thread()
        
        # Create a future that will be resolved by the nextValidId callback
        connection_future = asyncio.get_running_loop().create_future()
        self._pending_requests['connection'] = RequestContext(reqId=-1, future=connection_future)

        # Start the message dispatcher
        self.dispatcher_task = asyncio.create_task(self._dispatch_incoming_messages())

        try:
            # Wait for nextValidId, which confirms a good connection
            await asyncio.wait_for(connection_future, timeout=10)
            self.state = "OPERATIONAL"
            logging.info("IBKR Bridge is now OPERATIONAL.")
        except asyncio.TimeoutError:
            logging.error("Connection to IBKR timed out. Failed to receive nextValidId.")
            await self.disconnect()
            self.state = "DISCONNECTED"
            raise ConnectionError("IBKR connection timed out.")

    async def disconnect(self):
        """
        Gracefully disconnects from the IBKR Gateway and shuts down.
        """
        if self.state == "DISCONNECTED":
            return
            
        logging.info("Disconnecting from IBKR...")
        self.state = "DISCONNECTED"

        if self.dispatcher_task:
            self.dispatcher_task.cancel()
        
        self.outgoing_queue.put({'type': 'STOP'})
        if self.api_thread and self.api_thread.is_alive():
            self.api_thread.join(timeout=5)
        
        self.client.disconnect()
        logging.info("IBKR Bridge disconnected.")

    async def request_news_providers(self) -> list:
        """
        Requests the list of news providers the account is permissioned for.
        """
        logging.info("Requesting news providers...")
        future = await self._send_request('REQ_NEWS_PROVIDERS')
        response = await future
        return response.get('data', {}).get('providers', [])

    async def subscribe_to_news_feed(self, provider_code: str):
        """
        Subscribes to a real-time broadtape news feed.
        """
        req_id = self._get_next_req_id()
        contract = Contract()
        contract.secType = "NEWS"
        contract.exchange = provider_code
        # The symbol is often ignored, but we can set it for completeness
        contract.symbol = f"{provider_code}_ALL"
        
        request = {
            'type': 'SUBSCRIBE_NEWS_FEED',
            'reqId': req_id,
            'contract': contract
        }
        self.outgoing_queue.put(request)
        logging.info(f"Sent subscription request for news provider: {provider_code} with reqId {req_id}")

    async def fetch_historical_data(self, contract: Contract, duration: str, bar_size: str) -> list:
        """
        Requests a batch of historical candle data.
        """
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
        response = await future
        return response.get('data', [])

    async def place_order(self, contract: Contract, order: Order) -> int:
        """
        Places a new trade order.
        """
        order_id = self._get_next_order_id()
        order.orderId = order_id
        
        request = {
            'type': 'PLACE_ORDER',
            'reqId': order_id, # Use orderId as reqId for this specific request
            'contract': contract,
            'order': order
        }
        self.outgoing_queue.put(request)
        logging.info(f"Sent request to place order {order_id} for {contract.symbol}")
        return order_id
    
    # --- Internal Core Logic Methods ---

    def _start_api_thread(self):
        """
        Creates and starts the dedicated thread for the EClient loop.
        """
        self.api_thread = threading.Thread(target=self.client.run_loop, args=(self.outgoing_queue, self.host, self.port, self.client_id), daemon=True)
        self.api_thread.start()
        logging.info("IBKR API thread started.")

    async def _dispatch_incoming_messages(self):
        """
        The main async task that processes messages from the EWrapper.
        """
        logging.info("Async message dispatcher started.")
        while self.state != "DISCONNECTED":
            try:
                message = await asyncio.to_thread(self.incoming_queue.get)
                
                msg_type = message.get('type')
                reqId = message.get('data', {}).get('reqId')

                if msg_type in ['HISTORICAL_DATA_BAR', 'HISTORICAL_DATA_END', 'NEWS_PROVIDERS', 'ERROR']:
                    self._handle_response_message(message)
                elif msg_type == 'NEWS_TICK':
                    self._handle_streaming_message(message)
                else: # System messages, order updates, etc.
                    self._handle_system_message(message)

            except asyncio.CancelledError:
                logging.info("Message dispatcher stopping.")
                break
            except Exception:
                logging.exception("Error in message dispatcher.")

    def _handle_response_message(self, message: dict):
        """
        Handles messages that correspond to a pending request.
        """
        reqId = message.get('data', {}).get('reqId')
        context = self._pending_requests.get(reqId)
        if not context:
            return # Ignore messages without a pending request

        if message['type'] == 'HISTORICAL_DATA_BAR':
            # Aggregate historical data bars
            if context.data_aggregator is None:
                context.data_aggregator = []
            context.data_aggregator.append(message['data']['bar'])
        
        elif message['type'] == 'HISTORICAL_DATA_END':
            # Resolve the future with the aggregated data
            result = {'reqId': reqId, 'data': context.data_aggregator or []}
            context.future.set_result(result)
            self._pending_requests.pop(reqId, None)

        elif message['type'] == 'ERROR' and not context.future.done():
            # If an error is associated with a pending request, fail the future
            context.future.set_exception(RuntimeError(message['data']['message']))
            self._pending_requests.pop(reqId, None)

        else: # For simple, single-response messages
            if not context.future.done():
                context.future.set_result(message)
                self._pending_requests.pop(reqId, None)

    def _handle_streaming_message(self, message: dict):
        """
        Handles messages that are part of a continuous stream (e.g., news).
        """
        if message['type'] == 'NEWS_TICK':
            if self.news_handler_callback and asyncio.iscoroutinefunction(self.news_handler_callback):
                asyncio.create_task(self.news_handler_callback(message['data']['article']))

    def _handle_system_message(self, message: dict):
        """
        Handles system-level messages like errors or the nextValidId.
        """
        if message['type'] == 'NEXT_VALID_ID':
            self._set_initial_order_id(message['data']['orderId'])
            # Resolve the connection future
            if 'connection' in self._pending_requests:
                self._pending_requests.pop('connection').future.set_result(True)
        
        elif message['type'] == 'ERROR':
            logging.error(f"IBKR Error. Request ID: {message['data']['reqId']}, Code: {message['data']['code']}, Message: {message['data']['message']}")
        
        # TODO: Handle other system messages like order statuses by passing them
        # to the relevant service (e.g., a Position Manager callback)

    async def _send_request(self, request_type: str, **kwargs) -> asyncio.Future:
        """
        A generic, internal helper for making a request/response call.
        """
        req_id = self._get_next_req_id()
        future = asyncio.get_running_loop().create_future()
        
        self._pending_requests[req_id] = RequestContext(reqId=req_id, future=future)
        
        request = {
            'type': request_type,
            'reqId': req_id,
            **kwargs
        }
        self.outgoing_queue.put(request)
        return future

    # --- ID Generation Methods ---

    def _get_next_req_id(self) -> int:
        """Returns a new, unique, thread-safe request ID."""
        with self._req_id_lock:
            self._next_req_id += 1
            return self._next_req_id

    def _get_next_order_id(self) -> int:
        """Returns a new, unique, thread-safe order ID."""
        with self._order_id_lock:
            if self._next_order_id == -1:
                raise ConnectionError("Cannot get next order ID: nextValidId has not been received from IBKR yet.")
            
            current_id = self._next_order_id
            self._next_order_id += 1
            return current_id
    
    def _set_initial_order_id(self, order_id: int):
        """Sets the starting order ID after receiving the nextValidId callback."""
        with self._order_id_lock:
            if self._next_order_id == -1: # Only set it the first time
                self._next_order_id = order_id
                logging.info(f"Initial order ID set to: {order_id}")