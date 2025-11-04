import asyncio
import logging
import aiohttp

from momentum_bot.services.ai import extract_symbols_with_ai

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class NewsHandler:
    def __init__(self, raw_news_queue: asyncio.Queue, processed_news_queue: asyncio.Queue):
        self.raw_news_queue = raw_news_queue
        self.processed_news_queue = processed_news_queue
        self.http_session: aiohttp.ClientSession | None = None
        self._processing_task: asyncio.Task | None = None
        logging.info("NewsHandler initialized.")

    async def start(self):
        """Starts the news handler, creates an HTTP session, and begins processing articles."""
        logging.info("NewsHandler started. Creating HTTP session...")
        self.http_session = aiohttp.ClientSession()
        self._processing_task = asyncio.create_task(self._process_news_articles())
        logging.info("NewsHandler is now processing news articles.")

    async def stop(self):
        """Stops the news handler and gracefully closes the HTTP session."""
        logging.info("Stopping NewsHandler...")
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass # Expected
        if self.http_session:
            await self.http_session.close()
            logging.info("HTTP session closed.")
        logging.info("NewsHandler stopped.")

    async def _process_news_articles(self):
        if not self.http_session:
            logging.error("HTTP session is not available. Cannot process news.")
            return

        while True:
            try:
                news_data = await self.raw_news_queue.get()
                req_id = news_data.get("reqId")
                article_text = news_data.get("article")

                if not article_text:
                    logging.warning(f"NewsHandler: Received empty news article for ReqId {req_id}. Skipping.")
                    self.raw_news_queue.task_done()
                    continue

                logging.info(f"NewsHandler: Processing news article (ReqId: {req_id}) with AI...")
                
                try:
                    # Replace the old parser with the new AI-based one
                    tickers = await extract_symbols_with_ai(article_text, session=self.http_session)
                    if tickers:
                        for ticker in tickers:
                            logging.info(f"NewsHandler: AI detected ticker {ticker}. Adding to processed queue.")
                            await self.processed_news_queue.put(ticker)
                    else:
                        logging.debug(f"NewsHandler: AI found no tickers in news article for ReqId {req_id}.")
                except Exception as e:
                    logging.error(f"NewsHandler: Error during AI parsing for ReqId {req_id}: {e}", exc_info=True)

                self.raw_news_queue.task_done()
            except asyncio.CancelledError:
                logging.info("NewsHandler processing task cancelled.")
                break
            except Exception as e:
                logging.error(f"NewsHandler: An unexpected error occurred in _process_news_articles: {e}", exc_info=True)

    def get_processed_news_queue(self):
        return self.processed_news_queue

