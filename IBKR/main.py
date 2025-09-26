from ibapi.client import EClient
from ibapi.wrapper import EWrapper
import time
import threading


class TestApp(EClient, EWrapper):
    def __init__(self):
        EClient.__init__(self, self)

    def nextValidId(self, orderId: int):
        self.orderId = orderId

    def nextId(self):
        self.orderId += 1
        return self.orderId
    

app = TestApp()
app.connect("localhost", 4001, 0)