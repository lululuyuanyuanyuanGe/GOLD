from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
import threading, time

class IBApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.ready = threading.Event()

    def nextValidId(self, orderId):
        print("Connected with nextValidId:", orderId)
        self.ready.set()

    def newsProviders(self, newsProviders):
        print("Got", len(newsProviders), "news providers")
        for p in newsProviders:
            print(" ", p.code, ":", p.name)

    def error(self, reqId, code, msg, advancedOrderReject=""):
        print("Error", code, ":", msg)

def main():
    app = IBApp()

    # 1) Connect first
    app.connect("127.0.0.1", 4001, 1)

    # 2) Start pump after connect
    pump = threading.Thread(target=app.run, daemon=False)
    pump.start()

    # 3) Wait for connection-ready signal
    if not app.ready.wait(timeout=10):
        print("Timeout waiting for nextValidId")
        app.disconnect()
        pump.join(timeout=2)
        return

    # 4) Make requests any time after ready
    app.reqNewsProviders()

    # 5) Keep main alive for callbacks to arrive
    time.sleep(1)

    app.disconnect()
    pump.join(timeout=2)

if __name__ == "__main__":
    main()
