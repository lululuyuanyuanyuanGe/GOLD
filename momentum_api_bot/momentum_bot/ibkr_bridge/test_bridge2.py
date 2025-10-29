import asyncio
import logging
from momentum_api_bot.momentum_bot.ibkr_bridge.bridge import IBKRBridge

# --- Configuration ---
# Make sure these match your IB Gateway settings
IBKR_HOST = '127.0.0.1'
IBKR_PORT = 4002  # Use 4002 for Gateway, 7497 for TWS
IBKR_CLIENT_ID = 25  # Use a unique client ID for testing

# --- Setup Basic Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# --- Define a Callback for Streaming Data (News) ---
async def news_handler_callback(article: str):
    """
    This is an asynchronous function that will be called by the bridge
    every time a new news article is received.
    """
    logging.info("-------> [CALLBACK] News Article Received! <-------")
    # In a real app, you would parse this XML
    print(article)
    logging.info("--------------------------------------------------")


async def main():
    """
    The main asynchronous function to run our test sequence.
    """
    logging.info("--- Starting IBKR Bridge Test Script ---")
    bridge = IBKRBridge(host=IBKR_HOST, port=IBKR_PORT, client_id=IBKR_CLIENT_ID)

    try:
        # 1. TEST CONNECTION
        # ------------------
        # This tests the entire startup sequence: thread creation, connection,
        # and waiting for the 'nextValidId' confirmation.
        logging.info("[TEST 1/4] Attempting to connect...")
        await bridge.connect()
        logging.info("[SUCCESS] Bridge is connected and operational.")
        
        # Give the connection a moment to settle
        await asyncio.sleep(2)

        # 2. TEST REQUEST/RESPONSE (using asyncio.Future)
        # ------------------------------------------------
        # This tests the entire request/response loop:
        # _send_request -> outgoing_queue -> client -> wrapper -> incoming_queue -> dispatcher -> future.set_result
        logging.info("[TEST 2/4] Requesting available news providers...")
        providers = await bridge.request_news_providers()
        
        if providers:
            logging.info(f"[SUCCESS] Received news providers: {[p['name'] for p in providers]}")
        else:
            logging.warning("[RESULT] Received an empty list of news providers. This is expected if you have no API news subscriptions.")
        
        await asyncio.sleep(2)

        # 3. TEST STREAMING SUBSCRIPTION (using a callback)
        # ---------------------------------------------------
        # This tests the "fire-and-forget" subscription and the dispatcher's
        # ability to route streaming messages to a registered callback.
        logging.info("[TEST 3/4] Subscribing to Briefing.com (BRFG) news feed...")
        
        # Register our async callback function with the bridge
        bridge.news_handler_callback = news_handler_callback
        
        # Subscribe. Note: This call returns instantly and does not await a "response".
        await bridge.subscribe_to_news_feed('BRFG')
        
        logging.info("[SUCCESS] Subscription request sent. Now waiting for 60 seconds to see if any news articles arrive.")
        logging.info("If news arrives, the 'News Article Received!' message will appear.")
        await asyncio.sleep(60) # Wait for a minute

        # 4. TEST DISCONNECTION
        # ---------------------
        # This is handled in the 'finally' block to ensure it always runs.
        logging.info("[TEST 4/4] Test duration complete. Proceeding to disconnect.")

    except ConnectionError as e:
        logging.error(f"[FAILURE] Could not connect to IBKR Gateway: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred during the test: {e}", exc_info=True)
    finally:
        # This is crucial to ensure the API thread is shut down cleanly.
        if bridge.state != "DISCONNECTED":
            logging.info("--- Tearing down connection ---")
            await bridge.disconnect()
            logging.info("[SUCCESS] Bridge disconnected cleanly.")
    
    logging.info("--- IBKR Bridge Test Script Finished ---")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Test interrupted by user.")