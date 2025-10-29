import time
import logging
from ibapi.client import EClient
from ibapi.wrapper import EWrapper

# --- Configuration ---
# NOTE: These must match your running Gateway instance
IBKR_HOST = "127.0.0.1"
IBKR_PORT = 4002
IBKR_CLIENT_ID = 102 # Try a different ID if you suspect a conflict, e.g., 999

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TestWrapper(EWrapper):
    """
    The EWrapper subclass is used to receive messages from the TWS/Gateway.
    """
    def nextValidId(self, orderId: int):
        """
        This is the very first callback received after a successful connection.
        It signifies that the API connection is fully operational.
        """
        super().nextValidId(orderId)
        logging.info(f"SUCCESS: Connection is operational. Next Valid Order ID: {orderId}")
        # We can disconnect now that we've confirmed the connection works

    def connectAck(self):
        """Confirms the low-level socket connection."""
        logging.info("INFO: Low-level socket connection acknowledged.")

    def error(self, reqId, errorCode, errorString):
        """
        This callback is crucial for debugging. It receives error messages from TWS.
        """
        super().error(reqId, errorCode, errorString)
        logging.error(f"API ERROR - reqId: {reqId}, Code: {errorCode}, Message: '{errorString}'")

class TestClient(EClient):
    """
    The EClient subclass is used to send messages to the TWS/Gateway.
    """
    def __init__(self, wrapper):
        EClient.__init__(self, wrapper)

def main():
    """
    Main function to run the test.
    """
    logging.info("--- Starting Minimal IBKR Connection Test ---")
    
    # Instantiate the wrapper and the client
    wrapper = TestWrapper()
    client = TestClient(wrapper)

    # Connect to the TWS/Gateway
    logging.info(f"Attempting to connect to {IBKR_HOST}:{IBKR_PORT} with Client ID: {IBKR_CLIENT_ID}...")
    client.connect(IBKR_HOST, IBKR_PORT, IBKR_CLIENT_ID)

    # The TWS API runs in its own thread. We need to start it.
    # The run() method will block and process messages until disconnected.
    logging.info("Starting the client thread...")
    client.run()
    
    logging.info("--- Test Finished ---")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")