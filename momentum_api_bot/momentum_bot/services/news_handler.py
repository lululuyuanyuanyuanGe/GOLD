import asyncio
import logging
import xml.etree.ElementTree as ET
from momentum_bot.utils import parse_ibkr_news_xml
from momentum_bot.ibkr_connector import IBKRConnector

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class NewsHandler:
    def __init__(self, ibkr_connector: IBKRConnector, news_queue: asyncio.Queue):
        self.ibkr_connector = ibkr_connector
        self.news_queue = news_queue
        # Remove the debug print statement
        # print(dir(self.ibkr_connector.ib))
        self.ibkr_connector.ib.tickNewsEvent += self._on_tick_news_event
        logging.info("NewsHandler initialized and subscribed to IBKR newsArticleEvent.")

    async def _on_tick_news_event(self, tickerId, timeStamp, providerCode, articleId, headline, hasMore):
        """Callback for incoming news ticks."""
        logging.info(f"NewsHandler: Received news tick: {headline} (Provider: {providerCode}, Article ID: {articleId})")

        if not articleId:
            logging.warning("NewsHandler: Received news tick without article ID. Skipping.")
            return

        try:
            # Fetch the full news article
            article = await self.ibkr_connector.ib.reqNewsArticleAsync(providerCode, articleId)
            if article and article.articleText:
                # Assuming the articleText is XML content
                tickers = parse_ibkr_news_xml(article.articleText)

                if tickers:
                    for ticker in tickers:
                        logging.info(f"NewsHandler: Detected ticker {ticker} from news article. Adding to queue.")
                        await self.news_queue.put(ticker)
                else:
                    logging.info("NewsHandler: No tickers found in news article.")
            else:
                logging.warning(f"NewsHandler: Could not fetch full article for ID {articleId} or article text is empty.")

        except Exception as e:
            logging.error(f"NewsHandler: An unexpected error occurred during news article fetching/processing: {e}", exc_info=True)

    async def start(self):
        """Starts the news handler, which primarily listens via the IBKRConnector's event system."""
        logging.info("NewsHandler started. Waiting for news articles...")
        # The actual subscription to news topics will happen via IBKRConnector's subscribe_to_news method
        # which will be called from main.py or a higher-level orchestrator.

