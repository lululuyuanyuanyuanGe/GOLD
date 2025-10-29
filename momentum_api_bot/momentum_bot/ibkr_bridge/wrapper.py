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
from ibapi.contract import Contract
from ibapi.order import Order, OrderState
from ibapi.ticktype import TickTypeEnum
from ibapi.commission_report import CommissionReport
import queue
import logging

class IBWrapper(EWrapper):
    """
    Subclass of EWrapper, designed to redirect all incoming events into a
    single, thread-safe queue for consumption by the main asyncio application.
    """

    def __init__(self, incoming_messages_queue: queue.Queue):
        """
        Initializes the EWrapper.

        Args:
            incoming_messages_queue: A thread-safe queue.Queue instance.
                                     All callback methods will put their
                                     data into this queue.
        """
        # Call the parent __init__ from EWrapper
        # Store the queue as an instance variable.
        pass

    # --- Core Callback Methods ---

    def error(self, reqId: int, errorCode: int, errorString: str):
        """
        EWrapper method that is called for any API error.

        This is a critical method for logging and error handling. It packages
        error information and puts it onto the queue.

        Args:
            reqId: The request ID associated with the error, or -1 for system messages.
            errorCode: The numeric error code.
            errorString: The human-readable error message.
        """
        pass

    def nextValidId(self, orderId: int):
        """
        EWrapper method that provides the next valid ID for placing an order.

        This is typically received immediately after a successful connection.
        We capture this and put it on the queue so the main application knows
        it's safe to start placing orders.

        Args:
            orderId: The next valid order ID.
        """
        pass

    # --- News Callback Methods ---

    def newsArticle(self, reqId: int, articleType: int, articleText: str):
        """
        EWrapper method called when a news article is received.

        This is for DEPRECATED news requests. The primary news feed will
        come through tick-by-tick data.

        Args:
            reqId: The request ID of the news subscription.
            articleType: The type of article (0 for plain text, 1 for HTML).
            articleText: The content of the article.
        """
        pass
    
    def newsProviders(self, newsProviders):
        """
        EWrapper method that returns the list of available news providers.

        This is the response to the EClient.reqNewsProviders() call.

        Args:
            newsProviders: A list of NewsProvider objects.
        """
        pass

    # --- Order and Position Callback Methods ---

    def openOrder(self, orderId: int, contract: Contract, order: Order, orderState: OrderState):
        """
        EWrapper method that provides data about an open order.

        This is called in response to reqOpenOrders() and after placing a new
        order.

        Args:
            orderId: The order's unique ID.
            contract: The Contract for the order.
            order: The Order object itself.
            orderState: The state of the order (e.g., Submitted, Filled).
        """
        pass

    def orderStatus(self, orderId: int, status: str, filled: float, remaining: float, avgFillPrice: float, permId: int, parentId: int, lastFillPrice: float, clientId: int, whyHeld: str, mktCapPrice: float):
        """
        EWrapper method called when the status of an order changes.

        This is a critical callback for tracking fills and order lifecycle.

        Args:
            orderId: The order's unique ID.
            status: The new status of the order (e.g., 'Filled', 'Cancelled').
            filled: The number of shares that have been filled.
            remaining: The number of shares remaining to be filled.
            avgFillPrice: The average price of the filled shares.
            ...and other status-related fields.
        """
        pass

    def position(self, account: str, contract: Contract, position: float, avgCost: float):
        """
        EWrapper method that provides information about a position in the portfolio.

        This is the response to the EClient.reqPositions() call.

        Args:
            account: The account ID.
            contract: The Contract of the position.
            position: The number of shares held (can be positive or negative).
            avgCost: The average cost of the position.
        """
        pass

    # --- Market Data Callback Methods ---

    def tickPrice(self, reqId: int, tickType: int, price: float, attrib):
        """
        EWrapper method called with real-time price updates for a subscription.

        Args:
            reqId: The request ID of the market data subscription.
            tickType: The type of price tick (e.g., Bid, Ask, Last).
            price: The actual price value.
            attrib: Tick attributes.
        """
        pass
    
    def tickSize(self, reqId: int, tickType: int, size: int):
        """
        EWrapper method called with real-time size updates (e.g., volume).

        Args:
            reqId: The request ID of the market data subscription.
            tickType: The type of size tick (e.g., Volume, BidSize, AskSize).
            size: The actual size value.
        """
        pass

    def tickString(self, reqId: int, tickType: int, value: str):
        """
        EWrapper method for tick types that return a string. This includes
        real-time news headlines.

        This is the primary callback for our news feed.

        Args:
            reqId: The request ID of the subscription.
            tickType: The type of tick. For news, this is often '47' (RT_NEWS_ALERT).
            value: The string data, which for news, is the XML article.
        """
        pass

    def historicalData(self, reqId: int, bar):
        """
        EWrapper method that provides a single bar of historical data.

        This method is called repeatedly for each bar in the requested dataset.

        Args:
            reqId: The request ID of the historical data request.
            bar: An object containing the bar data (Date, Open, High, Low, Close, Volume, etc.).
        """
        pass

    def historicalDataEnd(self, reqId: int, start: str, end: str):
        """
        EWrapper method called after all historical data bars for a request
        have been received.

        This is a crucial signal to the main application that the historical
        data request is complete.

        Args:
            reqId: The request ID of the historical data request.
            start: The start date of the data.
            end: The end date of the data.
        """
        pass

    # ... other EWrapper methods can be implemented as needed, but they will all
    # follow the same pattern: package the arguments into a dictionary and
    # put it onto the incoming_messages_queue. ...