from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.common import TickerId, BarData
from ibapi.contract import Contract
from ibapi.order import Order
import queue
import logging

class IBWrapper(EWrapper):
    def __init__(self, incoming_queue: queue.Queue):
        EWrapper.__init__(self)
        self.incoming_queue = incoming_queue
        self.nextValidOrderId = -1
        self.historical_data_map = {} # To store historical data by reqId
        self.account_summary_map = {} # To store account summary by reqId
        self.news_providers = [] # To store news providers

    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        self.nextValidOrderId = orderId
        logging.info(f"Next Valid Order ID: {orderId}")
        self.incoming_queue.put({"type": "nextValidId", "orderId": orderId})
    