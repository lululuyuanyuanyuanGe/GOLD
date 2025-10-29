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
    
    def fetch_market_data(self):
        """Fetch the corresponding data needed based on the algorithm we defined to detect the price shock"""
        pass

    def execute_an_order(self):
        """Place the order or sell an order, it do the corresponding order executions"""
        pass

    def subscribe_news_provider(self):
        """Subscibe to the news providers of a given list"""
        pass

    def check_account_info(self):
        """Check the account information, postiion, balance, etc.""" 
        pass

    def _run_api_loop(self):
        logging.info("Starting IBKR API thread...")
        self.client.connect(self.host, self.port, self.client_id)
        if self.client.isConnected():
            self._is_connected.set()
            logging.info("IBKR API client connected.")
        self.client.run()
        logging.info("IBKR API thread stopped.")

    def start(self):
        pass


   