"""
Contains the IBClient class, which subclasses ibapi.client.EClient.

This class is responsible for the low-level communication of sending requests
to the TWS/Gateway. It is designed to be run in its own dedicated thread,
managed by the IBKRBridge. Its primary function is to run the socket client
event loop and process a queue of outgoing requests.
"""

from ibapi.client import EClient
from ibapi.order import Order
from ibapi.contract import Contract
import queue
import logging
import time

class IBClient(EClient):
    """
    Subclass of EClient, enhanced to integrate with our threaded, queue-based
    architecture. It connects the EWrapper implementation and manages the
    outgoing request queue.
    """

    def __init__(self, wrapper):
        """
        Initializes the EClient with the associated EWrapper.

        Args:
            wrapper: An instance of our custom IBWrapper class.
        """
        EClient.__init__(self, wrapper)

    def run_loop(self, outgoing_requests_queue: queue.Queue, host: str, port: int, client_id: int):
        """
        This is the main event loop for the EClient thread.

        It continuously checks a queue for new outgoing requests from the main
        asyncio application and dispatches them to the appropriate EClient
        methods. This method is the "heartbeat" of the client thread.
        """
        self.connect(host, port, client_id)
        logging.info("IBClient thread started and connected.")
        
        while self.isConnected():
            try:
                # Use a timeout to remain responsive to the connection status
                request = outgoing_requests_queue.get(timeout=1.0)
                if request.get('type') == 'STOP':
                    logging.info("IBClient thread received STOP signal.")
                    break
                self._process_request(request)
            except queue.Empty:
                # No new requests, continue loop
                continue
            except Exception:
                logging.exception("Exception in IBClient run_loop.")
        
        logging.info("IBClient run_loop finished.")


    def _process_request(self, request: dict):
        """
        Internal dispatcher method to process a single request dictionary.

        This method acts as a router. It inspects the 'type' of the request
        and calls the corresponding low-level EClient method with the provided
        parameters.
        """
        request_type = request.get('type')
        if not request_type:
            logging.warning(f"Received request without a type: {request}")
            return

        # Pop the type to clean up kwargs for the execute methods
        request.pop('type', None)

        if request_type == 'REQ_POSITIONS':
            self._execute_req_positions()
        elif request_type == 'CANCEL_POSITIONS':
            self._execute_cancel_positions()
        elif request_type == 'PLACE_ORDER':
            self._execute_place_order(**request)
        elif request_type == 'CANCEL_ORDER':
            self._execute_cancel_order(**request)
        elif request_type == 'REQ_OPEN_ORDERS':
            self._execute_req_open_orders()
        elif request_type == 'REQ_MKT_DATA':
            self._execute_req_mkt_data(**request)
        elif request_type == 'CANCEL_MKT_DATA':
            self._execute_cancel_mkt_data(**request)
        elif request_type == 'REQ_HISTORICAL_DATA':
            self._execute_req_historical_data(**request)
        elif request_type == 'SUBSCRIBE_NEWS_FEED':
            self._execute_subscribe_news_feed(**request)
        elif request_type == 'UNSUBSCRIBE_NEWS_FEED':
            self._execute_unsubscribe_news_feed(**request)
        elif request_type == 'REQ_NEWS_PROVIDERS':
            self._execute_req_news_providers()
        else:
            logging.warning(f"Unknown request type received: {request_type}")

    # --- Specific Request Handling Methods ---

    def _execute_req_positions(self):
        """Calls the underlying EClient.reqPositions() method."""
        self.reqPositions()

    def _execute_cancel_positions(self):
        """Calls the underlying EClient.cancelPositions() method."""
        self.cancelPositions()

    def _execute_place_order(self, reqId: int, contract: Contract, order: Order):
        """Calls the underlying EClient.placeOrder method."""
        self.placeOrder(reqId, contract, order)

    def _execute_cancel_order(self, orderId: int):
        """Calls the underlying EClient.cancelOrder method."""
        self.cancelOrder(orderId)
    
    def _execute_req_open_orders(self):
        """Calls the underlying EClient.reqOpenOrders() method."""
        self.reqOpenOrders()

    def _execute_req_mkt_data(self, reqId: int, contract: Contract, genericTickList: str, snapshot: bool, regulatorySnapshot: bool):
        """Calls the underlying EClient.reqMktData method."""
        self.reqMktData(reqId, contract, genericTickList, snapshot, regulatorySnapshot, [])

    def _execute_cancel_mkt_data(self, reqId: int):
        """Calls the underlying EClient.cancelMktData method."""
        self.cancelMktData(reqId)

    def _execute_req_historical_data(self, reqId: int, contract: Contract, durationStr: str, barSizeSetting: str, whatToShow: str, useRTH: int, formatDate: int, keepUpToDate: bool, endDateTime: str = ''):
        """Calls the underlying EClient.reqHistoricalData method."""
        self.reqHistoricalData(reqId, contract, endDateTime, durationStr, barSizeSetting, whatToShow, useRTH, formatDate, keepUpToDate, [])

    def _execute_subscribe_news_feed(self, reqId: int, contract: Contract):
        """Subscribes to a real-time broadtape news feed."""
        # This is a specialized use of reqMktData.
        # "292" is the generic tick type for broadtape news.
        self.reqMktData(reqId, contract, "292", False, False, [])

    def _execute_unsubscribe_news_feed(self, reqId: int):
        """Unsubscribes from a real-time news feed."""
        # This is an alias for cancelMktData.
        self.cancelMktData(reqId)

    def _execute_req_news_providers(self):
        """Calls the underlying EClient.reqNewsProviders() method."""
        self.reqNewsProviders()