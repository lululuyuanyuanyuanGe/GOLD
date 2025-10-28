import asyncio
import logging
import yaml
import sys
import os

# Add the parent directory to sys.path to make momentum_bot discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from momentum_bot.ibkr_connector import IBKRConnector
from momentum_bot.services.news_handler import NewsHandler
from momentum_bot.services.detection_engine import DetectionEngine
from momentum_bot.services.execution_service import ExecutionService
from momentum_bot.services.position_manager import PositionManager
from momentum_bot.database import init_db

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
            "providers": ['BZ'], # Example: Add other providers as needed
            "symbols": ['SPY', 'QQQ'] # Symbols to subscribe to news for
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

    # Initialize queues
    news_queue = asyncio.Queue()
    execution_queue = asyncio.Queue()

    # Initialize components
    ibkr_connector = IBKRConnector(
        host=config["ibkr"]["host"],
        port=config["ibkr"]["port"],
        client_id=config["ibkr"]["client_id"]
    )
    news_handler = NewsHandler(ibkr_connector, news_queue)
    detection_engine = DetectionEngine(ibkr_connector, news_queue, execution_queue, num_workers=config["detection_engine"]["num_workers"])
    execution_service = ExecutionService(ibkr_connector, execution_queue, Session)
    position_manager = PositionManager(ibkr_connector, execution_service, Session)

    # Start all services
    await ibkr_connector.connect_async()
    await news_handler.start()
    # Subscribe to news after connector is operational
    await ibkr_connector.subscribe_to_news_providers_test(config["news"]["providers"])
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
        logging.info("Shutting down Momentum API Bot...")
        # Stop services gracefully
        await position_manager.stop()
        await execution_service.stop()
        await detection_engine.stop()
        # news_handler doesn't have a stop method as it's event-driven
        await ibkr_connector.disconnect()
        logging.info("Momentum API Bot shutdown complete.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Application exit due to KeyboardInterrupt.")
    except Exception as e:
        logging.error(f"An unhandled error occurred in main: {e}", exc_info=True)
