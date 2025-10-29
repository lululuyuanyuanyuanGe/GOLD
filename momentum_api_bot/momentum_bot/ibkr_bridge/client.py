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
        super().__init__(wrapper)
