import asyncio
import logging
import xml.etree.ElementTree as ET
from momentum_bot.utils import parse_ibkr_news_xml
from ibapi.contract import Contract

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class NewsHandler:
    def __init__(self, news_processing_queue: asyncio.Queue):
        self.news_processing_queue = news_processing_queue
        self.processed_news_queue = asyncio.Queue() # To pass processed tickers to DetectionEngine
        logging.info("NewsHandler initialized.")

    async def start(self):
        """Starts the news handler, which primarily listens via the news_processing_queue."""
        logging.info("NewsHandler started. Waiting for news articles...")
        asyncio.create_task(self._process_news_articles())

    async def _process_news_articles(self):
        while True:
            try:
                message = await self.news_processing_queue.get()
                message_type = message.get("type")

                if message_type == "newsArticle":
                    req_id = message.get("reqId")
                    article_type = message.get("data", {}).get("articleType")
                    article_text = message.get("data", {}).get("articleText")
                    headline = message.get("data", {}).get("headline")
                    extra_data = message.get("data", {}).get("extraData")

                    logging.info(f"NewsHandler: Processing news article (ReqId: {req_id}, Headline: {headline})")

                    if not article_text:
                        logging.warning(f"NewsHandler: Received news article without text for ReqId {req_id}. Skipping.")
                        continue

                    try:
                        tickers = parse_ibkr_news_xml(article_text)
                        if tickers:
                            for ticker in tickers:
                                logging.info(f"NewsHandler: Detected ticker {ticker} from news article. Adding to processed queue.")
                                await self.processed_news_queue.put(ticker)
                        else:
                            logging.info(f"NewsHandler: No tickers found in news article for ReqId {req_id}.")
                    except Exception as e:
                        logging.error(f"NewsHandler: Error parsing news XML for ReqId {req_id}: {e}", exc_info=True)
                else:
                    logging.warning(f"NewsHandler: Received unexpected message type: {message_type}")

                self.news_processing_queue.task_done()
            except asyncio.CancelledError:
                logging.info("NewsHandler _process_news_articles task cancelled.")
                break
            except Exception as e:
                logging.error(f"NewsHandler: An unexpected error occurred in _process_news_articles: {e}", exc_info=True)

    async def get_processed_news(self):
        return await self.processed_news_queue.get()

    def get_processed_news_queue(self):
        return self.processed_news_queue

