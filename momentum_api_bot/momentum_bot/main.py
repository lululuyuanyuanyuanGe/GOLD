import asyncio
import logging
import yaml
import sys
import os

# Add the parent directory to sys.path to make momentum_bot discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from momentum_bot.ibkr_bridge.bridge import IBKRBridge
from momentum_bot.services.news_handler import NewsHandler
from momentum_bot.services.detection_engine import DetectionEngine
from momentum_bot.services.execution_service import ExecutionService
from momentum_bot.services.position_manager import PositionManager
from momentum_bot.database import init_db
from ibapi.contract import Contract

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def main():
    logging.info("Starting Momentum API Bot...")

    # Load configuration (placeholder for now)
    config = {
        "ibkr": {
            "host": "127.0.0.1",
            "port": 4001,
            "client_id": 1
        },
        "detection_engine": {
            "num_workers": 5
        },
        "position_manager": {
            "monitor_interval": 5
        },
        "database": {
            "url": f"sqlite:///{os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'trades.db'))}"
        },
        "news": {
            "providers": ['BZ'] # Example: Add other providers as needed
        }
    }
    try:
        with open("config/config.yaml", 'r') as f:
            loaded_config = yaml.safe_load(f)
            if loaded_config:
                config.update(loaded_config)
                logging.info("Configuration loaded from config/config.yaml")
    except FileNotFoundError:
        logging.warning("config/config.yaml not found. Using default configuration.")
    except Exception as e:
        logging.error(f"Error loading configuration: {e}. Using default configuration.")

    # Initialize database
    Session = init_db(config["database"]["url"])
    logging.info(f"Database initialized at {config["database"]["url"]}")

    # Initialize components
    ibkr_bridge = IBKRBridge(
        host=config["ibkr"]["host"],
        port=config["ibkr"]["port"],
        client_id=config["ibkr"]["client_id"]
    )

    # The incoming_queue from IBKRBridge will be consumed by a main events task
    # that then puts relevant messages onto an asyncio.Queue for the NewsHandler.
    # The outgoing_queue of IBKRBridge will be used by DetectionEngine and ExecutionService.
    ibkr_incoming_queue = ibkr_bridge.get_incoming_queue() # Thread-safe queue from IBKR API thread
    ibkr_outgoing_queue = ibkr_bridge.outgoing_queue # Thread-safe queue to IBKR API thread

    # Asyncio queues for inter-service communication within the asyncio loop
    news_processing_queue = asyncio.Queue() # News items after initial processing by events
    execution_request_queue = asyncio.Queue() # Requests from DetectionEngine to ExecutionService

    # Initialize services
    news_handler = NewsHandler(news_processing_queue)
    detection_engine = DetectionEngine(ibkr_bridge, news_handler.get_processed_news_queue(), execution_request_queue, num_workers=config["detection_engine"]["num_workers"])
    execution_service = ExecutionService(ibkr_bridge, execution_request_queue, Session)
    position_manager = PositionManager(ibkr_bridge, execution_service, Session)

    async def events_fetcher_from_IBKR():
        while True:
            try:
                # Get message from the synchronous IBKR incoming queue
                message = await asyncio.to_thread(ibkr_incoming_queue.get)
                logging.debug(f"events received message: {message['type']}")

                message_type = message.get("type")
                if message_type == "newsArticle":
                    await news_processing_queue.put(message)
                elif message_type == "error":
                    req_id = message.get("reqId", -1)
                    error_code = message.get("errorCode")
                    error_string = message.get("errorString")
                    logging.error(f"IBKR Error in events (ReqId: {req_id}, Code: {error_code}): {error_string}")
                elif message_type == "nextValidId":
                    logging.info(f"Received nextValidId: {message['orderId']}")
                elif message_type == "connectionClosed":
                    logging.warning("IBKR connection closed via events.")
                # Add other message types to handle as needed
                # For now, we'll just log them if not specifically handled
                else:
                    logging.debug(f"events handling unrouted message type: {message_type}")

                ibkr_incoming_queue.task_done()
            except Exception as e:
                logging.error(f"Error in events_fetcher_from_IBKR: {e}", exc_info=True)
            await asyncio.sleep(0.01) # Yield control

    # Start the IBKR Bridge thread
    ibkr_bridge.start()
    while not ibkr_bridge.is_connected():
        logging.info("Waiting for IBKR Bridge to connect...")
        await asyncio.sleep(1)
    logging.info("IBKR Bridge connected and operational.")

    # Start the events task
    events = asyncio.create_task(events_fetcher_from_IBKR())

    # Start other services
    await news_handler.start()
    await detection_engine.start()
    await execution_service.start()
    await position_manager.start(interval=config["position_manager"]["monitor_interval"])

    logging.info("Momentum API Bot services started. Press Ctrl+C to stop.")

    try:
        # Keep the main task alive
        while True:
            await asyncio.sleep(3600) # Sleep for an hour, or indefinitely
    except asyncio.CancelledError:
        logging.info("Main task cancelled.")
    except KeyboardInterrupt:
        logging.info("Application stopped by user (Ctrl+C).")
    finally:
        events.cancel()
        await events # Await cancellation
        logging.info("Shutting down Momentum API Bot...")
        # Stop services gracefully
        await position_manager.stop()
        await execution_service.stop()
        await detection_engine.stop()
        # news_handler doesn't have a stop method as it's event-driven
        ibkr_bridge.disconnect()
        logging.info("Momentum API Bot shutdown complete.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Application exit due to KeyboardInterrupt.")
    except Exception as e:
        logging.error(f"An unhandled error occurred in main: {e}", exc_info=True)
