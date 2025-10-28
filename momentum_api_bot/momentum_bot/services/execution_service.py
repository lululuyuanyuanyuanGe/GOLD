import asyncio
import logging
from momentum_bot.ibkr_connector import IBKRConnector
from momentum_bot.models import TradeSignal, Position
from momentum_bot.database import PositionRecord, Trade
from ib_insync import Contract, Order
from sqlalchemy.orm import sessionmaker
import datetime

# ... (rest of the imports and logging config)

class ExecutionService:
    def __init__(self, ibkr_connector: IBKRConnector, execution_queue: asyncio.Queue, Session: sessionmaker):
        self.ibkr_connector = ibkr_connector
        self.execution_queue = execution_queue
        self.Session = Session
        self.worker_task = None
        logging.info("ExecutionService initialized.")

    async def start(self):
        logging.info("Starting ExecutionService worker...")
        self.worker_task = asyncio.create_task(self._worker())

    async def _worker(self):
        logging.info("ExecutionService worker started.")
        while True:
            try:
                trade_signal: TradeSignal = await self.execution_queue.get()
                logging.info(f"ExecutionService: Received TradeSignal for {trade_signal.symbol}.")

                if not self.ibkr_connector.is_operational():
                    logging.warning(f"ExecutionService: IBKR connector not operational. Skipping trade for {trade_signal.symbol}.")
                    self.execution_queue.task_done()
                    continue

                # ... (Position Sizing Algorithm remains the same)

                logging.info(f"ExecutionService: Placing order for {trade_signal.symbol} (Action: {trade_signal.action}, Qty: {quantity}).")
                # Simulate order placement
                # filled_order = await self.ibkr_connector.place_order(contract, order)
                await asyncio.sleep(0.2) # Simulate order placement delay
                filled_order = {"contract": contract, "order": order, "orderStatus": {"status": "Filled"}, "avgFillPrice": trade_signal.entry_price} # Mock filled order

                if filled_order and filled_order["orderStatus"]["status"] == "Filled":
                    logging.info(f"ExecutionService: Order for {trade_signal.symbol} filled at {filled_order["avgFillPrice"]}.")
                    
                    with self.Session() as session:
                        # Create a new Trade record
                        trade_record = Trade(
                            symbol=trade_signal.symbol,
                            action=trade_signal.action,
                            quantity=quantity,
                            entry_price=filled_order["avgFillPrice"],
                            entry_timestamp=datetime.datetime.now(),
                            status="OPEN"
                        )
                        session.add(trade_record)
                        session.flush() # Flush to get the trade_record.id

                        # Create a PositionRecord and link it to the Trade (if needed, for now separate)
                        position_record = PositionRecord(
                            symbol=trade_signal.symbol,
                            quantity=quantity if trade_signal.action == "BUY" else -quantity,
                            avg_entry_price=filled_order["avgFillPrice"],
                            entry_timestamp=datetime.datetime.now(),
                            status="OPEN"
                        )
                        session.add(position_record)
                        session.commit()
                        logging.info(f"ExecutionService: Recorded new OPEN trade: {trade_record}")
                        logging.info(f"ExecutionService: Recorded new OPEN position in DB: {position_record}")
                else:
                    logging.warning(f"ExecutionService: Order for {trade_signal.symbol} not filled or failed.")

                self.execution_queue.task_done()
            except asyncio.CancelledError:
                logging.info("ExecutionService worker cancelled.")
                break
            except Exception as e:
                logging.error(f"ExecutionService: An error occurred: {e}", exc_info=True)

    async def stop(self):
        if self.worker_task:
            logging.info("Stopping ExecutionService worker...")
            self.worker_task.cancel()
            await self.worker_task
            logging.info("ExecutionService worker stopped.")
