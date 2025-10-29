
import asyncio
import logging
import unittest

from momentum_api_bot.momentum_bot.ibkr_bridge.bridge import IBKRBridge

# --- Configuration ---
# NOTE: These must match your running TWS/Gateway instance
IBKR_HOST = "127.0.0.1"
IBKR_PORT = 4002
IBKR_CLIENT_ID = 102

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TestIBKRBridge(unittest.IsolatedAsyncioTestCase):
    """
    Integration tests for the IBKRBridge.
    Requires a running TWS or Gateway instance.
    """

    async def asyncSetUp(self):
        """Set up a new bridge instance for each test."""
        self.bridge = IBKRBridge(host=IBKR_HOST, port=IBKR_PORT, client_id=IBKR_CLIENT_ID)
        self.news_received_event = asyncio.Event()
        self.received_article = None

    async def asyncTearDown(self):
        """Ensure disconnection after each test."""
        if self.bridge.state != "DISCONNECTED":
            await self.bridge.disconnect()

    async def test_01_connect_and_disconnect(self):
        """Test the basic connection and disconnection flow."""
        logging.info("--- Running test_01_connect_and_disconnect ---")
        try:
            await self.bridge.connect()
            self.assertEqual(self.bridge.state, "OPERATIONAL", "Bridge should be OPERATIONAL after connect")
        finally:
            await self.bridge.disconnect()
            self.assertEqual(self.bridge.state, "DISCONNECTED", "Bridge should be DISCONNECTED after disconnect")
            # Give the background thread a moment to fully shut down
            await asyncio.sleep(1)

    async def _news_handler_callback(self, article: str):
        """Callback for the bridge to handle incoming news."""
        logging.info(f"Received news article: {article[:100]}...")
        self.received_article = article
        self.news_received_event.set()

    async def test_02_subscribe_to_news(self):
        """
        Test subscribing to a news feed and receiving at least one article.
        NOTE: This test requires a subscription to the news provider being tested (e.g., BENZINGA).
        """
        logging.info("--- Running test_02_subscribe_to_news ---")
        
        # Set the callback on the bridge
        self.bridge.news_handler_callback = self._news_handler_callback

        await self.bridge.connect()
        self.assertEqual(self.bridge.state, "OPERATIONAL")

        # 1. Request available news providers
        providers = await self.bridge.request_news_providers()
        logging.info(f"Available news providers: {providers}")
        self.assertIsInstance(providers, list)

        # For this test, we'll use Benzinga News.
        # The test will fail if the account is not subscribed to this provider.
        news_provider_code = "BENZINGA"
        if not any(p['code'] == news_provider_code for p in providers):
            self.skipTest(f"Account not subscribed to the '{news_provider_code}' news provider.")

        # 2. Subscribe to the news feed
        logging.info(f"Subscribing to {news_provider_code} news feed...")
        await self.bridge.subscribe_to_news_feed(news_provider_code)

        # 3. Wait for a news article to arrive
        logging.info("Waiting for a news article to be received (timeout: 60s)...")
        try:
            await asyncio.wait_for(self.news_received_event.wait(), timeout=60)
        except asyncio.TimeoutError:
            self.fail("Test failed: Did not receive a news article within the timeout period.")

        # 4. Assert that an article was received
        self.assertTrue(self.news_received_event.is_set(), "News event should be set")
        self.assertIsNotNone(self.received_article, "Received article should not be None")
        self.assertIsInstance(self.received_article, str)
        logging.info("Successfully received a news article.")

if __name__ == "__main__":
    unittest.main()
