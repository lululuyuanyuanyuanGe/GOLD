"""
Contains the IBWrapper class, which subclasses ibapi.wrapper.EWrapper.

This class is the single point of entry for all incoming data from the TWS/Gateway.
Its only responsibility is to receive the data from the IBKR API thread,
package it into a standardized dictionary format, and put it onto a thread-safe
queue.

All business logic is handled by the asynchronous part of the application,
ensuring this class remains a simple, non-blocking data receiver.
"""

from ibapi.wrapper import EWrapper
from ibapi.contract import Contract, ContractDetails
from ibapi.order import Order
from ibapi.order_state import OrderState
from ibapi.ticktype import TickTypeEnum
from ibapi.commission_report import CommissionReport
import queue
import logging

class IBWrapper(EWrapper):
    """
    Subclass of EWrapper, designed to redirect all incoming events into a
    single, thread-safe queue for consumption by the main asyncio application.
    """

    # Fixed request ids for infrequently api calls
    REQ_ID_NEWS_PROVIDERS = -101

    def __init__(self, incoming_messages_queue: queue.Queue):
        """
        Initializes the EWrapper.

        Args:
            incoming_messages_queue: A thread-safe queue.Queue instance.
                                     All callback methods will put their
                                     data into this queue.
        """
        super().__init__()
        self.incoming_queue = incoming_messages_queue

    def _enqueue_message(self, msg_type: str, data: dict):
        """A standardized helper to put messages on the queue."""
        self.incoming_queue.put({'type': msg_type, 'data': data})

    # --- Core System & Connection Callbacks ---

    def error(self, reqId: int, errorCode: int, errorString: str, advancedOrderRejectJson: str = ""):
        """
        EWrapper method that is called for any API error. This method is also
        used for informational messages. We will filter out messages that are
        not true errors.
        See: https://interactivebrokers.github.io/tws-api/message_codes.html
        """
        # Overriding the EWrapper method. The `advancedOrderRejectJson` parameter was added in later API versions.

        # These are not errors, but informational messages.
        # We will log them and not treat them as errors.
        INFO_CODES = {
            2104, 2106, 2158, 2100, 2103, 2105, 2107, 2108, 2119, 2150,
            2168, 2169, 2170, 2157
        }

        if errorCode in INFO_CODES:
            logging.info(f"IBKR Info (Code: {errorCode}): {errorString}")
            return

        # For all other codes, treat it as an error.
        logging.error(f"IBKR Error (ReqId: {reqId}, Code: {errorCode}): {errorString}")
        self._enqueue_message('ERROR', {
            'reqId': reqId,
            'code': errorCode,
            'message': errorString,
        })

    def nextValidId(self, orderId: int):
        """EWrapper method that provides the next valid ID for placing an order."""
        logging.info("This is a test if the nextValidId() call successfully")
        self._enqueue_message('NEXT_VALID_ID', {'orderId': orderId})

    def connectAck(self):
        """EWrapper method called upon successful connection."""
        logging.info("IBKR API connection acknowledged.")
        # self._enqueue_message('CONNECTION_ACK', {})

    def connectionClosed(self):
        """EWrapper method called when the connection is closed."""
        logging.warning("IBKR API connection closed.")
        self._enqueue_message('CONNECTION_CLOSED', {})

    # --- News Callback Methods ---

    def newsProviders(self, newsProviders: list):
        """EWrapper method that returns the list of available news providers."""
        logging.info("WRAPPER: Received news providers list.")
        providers_data = [{'code': p.code, 'name': p.name} for p in newsProviders]
        
        # Add our fixed reqId to the message payload
        self._enqueue_message('NEWS_PROVIDERS', {
            'reqId': self.REQ_ID_NEWS_PROVIDERS, 
            'providers': providers_data
        })

    def tickString(self, reqId: int, tickType: int, value: str):
        """E-Wrapper method for tick types that return a string. This includes real-time news headlines."""
        # TickType 47 is RT_NEWS_ALERT
        if tickType == 47:
             self._enqueue_message('NEWS_TICK', {
                'reqId': reqId,
                'article': value
            })

    # --- Order and Position Callback Methods ---

    def openOrder(self, orderId: int, contract: Contract, order: Order, orderState: OrderState):
        """EWrapper method that provides data about an open order."""
        self._enqueue_message('OPEN_ORDER', {
            'orderId': orderId,
            'contract': contract,
            'order': order,
            'orderState': orderState
        })

    def openOrderEnd(self):
        """EWrapper method called after all open orders have been sent."""
        self._enqueue_message('OPEN_ORDER_END', {})
        
    def orderStatus(self, orderId: int, status: str, filled: float, remaining: float, avgFillPrice: float, permId: int, parentId: int, lastFillPrice: float, clientId: int, whyHeld: str, mktCapPrice: float):
        """E-Wrapper method called when the status of an order changes."""
        self._enqueue_message('ORDER_STATUS', {
            'orderId': orderId,
            'status': status,
            'filled': filled,
            'remaining': remaining,
            'avgFillPrice': avgFillPrice,
            'permId': permId
        })

    def position(self, account: str, contract: Contract, position: float, avgCost: float):
        """E-Wrapper method that provides information about a position in the portfolio."""
        self._enqueue_message('POSITION', {
            'account': account,
            'contract': contract,
            'position': position,
            'avgCost': avgCost
        })
    
    def positionEnd(self):
        """EWrapper method called after all position data has been sent."""
        self._enqueue_message('POSITION_END', {})

    def accountSummary(self, reqId: int, account: str, tag: str, value: str, currency: str):
        """E-Wrapper method providing account summary data."""
        self._enqueue_message('ACCOUNT_SUMMARY', {
            'reqId': reqId,
            'account': account,
            'tag': tag,
            'value': value,
            'currency': currency
        })
        
    def accountSummaryEnd(self, reqId: int):
        """EWrapper method called after all account summary data has been sent."""
        self._enqueue_message('ACCOUNT_SUMMARY_END', {'reqId': reqId})

    # --- Market Data Callback Methods ---

    def tickPrice(self, reqId: int, tickType: int, price: float, attrib):
        """EWrapper method called with real-time price updates for a subscription."""
        self._enqueue_message('TICK_PRICE', {
            'reqId': reqId,
            'tickType': TickTypeEnum.idx2name.get(tickType, tickType),
            'price': price
        })
    
    def tickSize(self, reqId: int, tickType: int, size: int):
        """EWrapper method called with real-time size updates (e.g., volume)."""
        self._enqueue_message('TICK_SIZE', {
            'reqId': reqId,
            'tickType': TickTypeEnum.idx2name.get(tickType, tickType),
            'size': size
        })

    def historicalData(self, reqId: int, bar):
        """EWrapper method that provides a single bar of historical data."""
        bar_data = {
            'date': bar.date,
            'open': bar.open,
            'high': bar.high,
            'low': bar.low,
            'close': bar.close,
            'volume': bar.volume,
            'barCount': bar.barCount,
            'average': bar.average
        }
        self._enqueue_message('HISTORICAL_DATA_BAR', {
            'reqId': reqId,
            'bar': bar_data
        })

    def historicalDataEnd(self, reqId: int, start: str, end: str):
        """E-Wrapper method called after all historical data bars for a request have been received."""
        self._enqueue_message('HISTORICAL_DATA_END', {
            'reqId': reqId,
            'start': start,
            'end': end
        })