from ibapi.client import EClient
from ibapi.wrapper import EWrapper
import threading
import time

class MinimalNewsApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        print("🔧 MinimalNewsApp initialized")
        
    def nextValidId(self, orderId: int):
        print(f"🟢 PYTHON: nextValidId called with orderId={orderId}")
        self.reqNewsProviders()
        
    def error(self, reqId, errorCode, errorString):
        print(f"🔴 PYTHON: Message {errorCode}: {errorString}")
        
    def newsProviders(self, newsProviders):
        print(f"🟢 PYTHON: Got {len(newsProviders)} news providers")
        for provider in newsProviders:
            print(f"  - {provider.code}: {provider.name}")

def main():
    app = MinimalNewsApp()
    
    print("🔌 Connecting first...")
    app.connect('127.0.0.1', 4001, clientId=1)
    
    # Check connection status
    print(f"📊 Connection status: isConnected={app.isConnected()}")
    
    if not app.isConnected():
        print("❌ Connection failed immediately")
        print("💡 Try:")
        print("   1. Restart IB Gateway")  
        print("   2. Check API settings are enabled")
        print("   3. Try different port (4002 for paper)")
        return
    
    print("✅ Connection established, now starting message loop...")
    
    # Now start the message processing
    try:
        # Use a simple loop instead of threading
        app.run()
    except KeyboardInterrupt:
        print("🛑 Interrupted by user")
    except Exception as e:
        print(f"💥 Exception in run(): {e}")
    finally:
        print("🔌 Disconnecting...")
        app.disconnect()

if __name__ == "__main__":
    main()
