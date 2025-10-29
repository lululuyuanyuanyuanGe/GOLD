import asyncio
import logging
import xml.etree.ElementTree as ET
from momentum_bot.utils import parse_ibkr_news_xml
from ibapi.contract import Contract

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class NewsHandler:
    def __init__(self, raw_news_queue: asyncio.Queue, processed_news_queue: asyncio.Queue):
        self.raw_news_queue = raw_news_queue
        self.processed_news_queue = processed_news_queue # To pass processed tickers to DetectionEngine
        logging.info("NewsHandler initialized.")

    async def start(self):
        """Starts the news handler, which primarily listens via the news_processing_queue."""
        logging.info("NewsHandler started. Waiting for news articles...")
        asyncio.create_task(self._process_news_articles())

    async def _process_news_articles(self):
        while True:
            try:
                # The message is now the raw data dict from the bridge
                news_data = await self.raw_news_queue.get()

                req_id = news_data.get("reqId")
                article_text = news_data.get("article")

                if not article_text:
                    logging.warning(f"NewsHandler: Received empty news article for ReqId {req_id}. Skipping.")
                    self.raw_news_queue.task_done()
                    continue

                logging.info(f"NewsHandler: Processing news article (ReqId: {req_id})")

                try:
                    tickers = parse_ibkr_news_xml(article_text)
                    if tickers:
                        for ticker in tickers:
                            logging.info(f"NewsHandler: Detected ticker {ticker} from news article. Adding to processed queue.")
                            await self.processed_news_queue.put(ticker)
                    else:
                        logging.debug(f"NewsHandler: No tickers found in news article for ReqId {req_id}.")
                except Exception as e:
                    logging.error(f"NewsHandler: Error parsing news XML for ReqId {req_id}: {e}", exc_info=True)

                self.raw_news_queue.task_done()
            except asyncio.CancelledError:
                logging.info("NewsHandler _process_news_articles task cancelled.")
                break
            except Exception as e:
                logging.error(f"NewsHandler: An unexpected error occurred in _process_news_articles: {e}", exc_info=True)

    def get_processed_news_queue(self):
        return self.processed_news_queue

