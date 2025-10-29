from ibapi.client import EClient
from ibapi.contract import Contract
from ibapi.order import Order
from ibkr_bridge.wrapper import IBWrapper

class IBClient(EClient):
    def __init__(self, wrapper):
        EClient.__init__(self, wrapper)

    def connect(self, host, port, clientId):
        super().connect(host, port, clientId)

    def disconnect(self):
        super().disconnect()

    def reqNewsProviders(self):
        super().reqNewsProviders()

    def reqMktData(self, reqId, contract, genericTickList, snapshot, regulatorySnapshot, mktDataOptions):
        super().reqMktData(reqId, contract, genericTickList, snapshot, regulatorySnapshot, mktDataOptions)

    def reqHistoricalData(self, reqId, contract, endDateTime, durationStr, barSizeSetting, whatToShow, useRTH, formatDate, keepUpToDate, chartOptions):
        super().reqHistoricalData(reqId, contract, endDateTime, durationStr, barSizeSetting, whatToShow, useRTH, formatDate, keepUpToDate, chartOptions)

    def placeOrder(self, orderId, contract, order):
        super().placeOrder(orderId, contract, order)

    def reqAccountSummary(self, reqId, group, tags):
        super().reqAccountSummary(reqId, group, tags)

    def cancelAccountSummary(self, reqId):
        super().cancelAccountSummary(reqId)
