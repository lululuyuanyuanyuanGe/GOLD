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

    # --- Queues for Inter-Service Communication ---
    raw_news_queue = asyncio.Queue()        # Bridge -> NewsHandler
    processed_news_queue = asyncio.Queue()  # NewsHandler -> DetectionEngine
    trade_signal_queue = asyncio.Queue()    # DetectionEngine -> ExecutionService

    # --- Initialize Components ---
    ibkr_bridge = IBKRBridge(
        host=config["ibkr"]["host"],
        port=config["ibkr"]["port"],
        client_id=config["ibkr"]["client_id"],
        raw_news_queue=raw_news_queue
    )

    news_handler = NewsHandler(
        raw_news_queue=raw_news_queue,
        processed_news_queue=processed_news_queue
    )

    detection_engine = DetectionEngine(ibkr_bridge, processed_news_queue, trade_signal_queue, num_workers=config["detection_engine"]["num_workers"])
    execution_service = ExecutionService(ibkr_bridge, trade_signal_queue, Session)
    position_manager = PositionManager(ibkr_bridge, execution_service, Session)


    # --- Start the Application ---
    # 1. Connect the IBKR Bridge
    await ibkr_bridge.connect()
    logging.info("IBKR Bridge connected and operational.")

    # 2. Subscribe to news feeds specified in the config
    news_providers = config.get("news", {}).get("providers", [])
    if news_providers:
        logging.info(f"Subscribing to news providers: {news_providers}")
        for provider in news_providers:
            await ibkr_bridge.subscribe_to_news_feed(provider)
    else:
        logging.warning("No news providers specified in config. No news will be processed.")

    # 3. Start other services
    await news_handler.start()
    # await detection_engine.start()
    # await execution_service.start()
    # await position_manager.start(interval=config["position_manager"]["monitor_interval"])

    logging.info("Momentum API Bot services started. Press Ctrl+C to stop.")

    try:
        # Keep the main task alive by waiting indefinitely
        await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        logging.info("Application shutdown initiated.")
    finally:
        logging.info("Shutting down services...")
        
        # The order of shutdown can be important
        if 'position_manager' in locals():
            await position_manager.stop()
        if 'execution_service' in locals():
            await execution_service.stop()
        if 'detection_engine' in locals():
            await detection_engine.stop()
        
        # Disconnect the bridge last
        if 'ibkr_bridge' in locals() and ibkr_bridge.state != "DISCONNECTED":
            await ibkr_bridge.disconnect()
            
        logging.info("Momentum API Bot shutdown complete.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Application exit due to KeyboardInterrupt.")
    except Exception as e:
        logging.error(f"An unhandled error occurred in main: {e}", exc_info=True)
