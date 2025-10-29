import asyncio
import logging
import asyncio
import logging
from momentum_bot.models import TradeSignal, Position
from momentum_bot.database import PositionRecord, Trade
from ibapi.contract import Contract
from ibapi.order import Order
from sqlalchemy.orm import sessionmaker
import datetime

# ... (rest of the imports and logging config)

class ExecutionService:
    def __init__(self, ibkr_bridge, execution_request_queue: asyncio.Queue, Session: sessionmaker):
        self.ibkr_bridge = ibkr_bridge
        self.execution_request_queue = execution_request_queue # This queue receives TradeSignals
        self.Session = Session
        self.worker_task = None
        self.pending_orders = {}
        logging.info("ExecutionService initialized.")

    async def start(self):
        logging.info("Starting ExecutionService worker...")
        self.worker_task = asyncio.create_task(self._worker())

    async def _worker(self):
        logging.info("ExecutionService worker started.")
        while True:
            try:
                trade_signal: TradeSignal = await self.execution_request_queue.get()
                logging.info(f"ExecutionService: Received TradeSignal for {trade_signal.symbol}.")

                if not self.ibkr_bridge.is_connected():
                    logging.warning(f"ExecutionService: IBKR bridge not connected. Skipping trade for {trade_signal.symbol}.")
                    self.execution_request_queue.task_done()
                    continue

                # Position Sizing Algorithm (remains the same)
                # For simplicity, let's assume a fixed quantity for now
                quantity = 10 # Example fixed quantity

                contract = Contract()
                contract.symbol = trade_signal.symbol
                contract.secType = 'STK'
                contract.exchange = 'SMART'
                contract.currency = 'USD'

                order = Order()
                order.action = trade_signal.action
                order.totalQuantity = quantity
                order.orderType = 'MKT' # Market order for simplicity
                order.eTradeOnly = False
                order.firmQuoteOnly = False

                logging.info(f"ExecutionService: Placing order for {trade_signal.symbol} (Action: {order.action}, Qty: {order.totalQuantity}, Type: {order.orderType}).")
                
                order_id = self.ibkr_bridge.place_order(contract, order)
                logging.info(f"ExecutionService: Order placed with OrderId: {order_id}")

                filled_order_status = None
                filled_avg_price = None

                # Wait for order status updates
                while True:
                    message = await asyncio.to_thread(self.ibkr_bridge.get_incoming_queue().get)
                    if message.get("type") == "orderStatus" and message.get("data", {}).get("orderId") == order_id:
                        status = message["data"]["status"]
                        logging.info(f"ExecutionService: Order {order_id} status: {status}")
                        if status == "Filled":
                            filled_order_status = status
                            filled_avg_price = message["data"]["avgFillPrice"]
                            self.ibkr_bridge.get_incoming_queue().task_done()
                            break
                        elif status in ["Cancelled", "ApiCancelled", "Inactive", "PendingCancel", "Rejected"]:
                            logging.warning(f"ExecutionService: Order {order_id} was {status}. Not filled.")
                            self.ibkr_bridge.get_incoming_queue().task_done()
                            break
                    elif message.get("type") == "error" and message.get("reqId") == order_id:
                        logging.error(f"ExecutionService: Error for order {order_id}: {message}")
                        self.ibkr_bridge.get_incoming_queue().task_done()
                        break
                    self.ibkr_bridge.get_incoming_queue().task_done()

                if filled_order_status == "Filled":
                    logging.info(f"ExecutionService: Order for {trade_signal.symbol} filled at {filled_avg_price}.")
                    
                    with self.Session() as session:
                        # Create a new Trade record
                        trade_record = Trade(
                            symbol=trade_signal.symbol,
                            action=trade_signal.action,
                            quantity=quantity,
                            entry_price=filled_avg_price,
                            entry_timestamp=datetime.datetime.now(),
                            status="OPEN"
                        )
                        session.add(trade_record)
                        session.flush() # Flush to get the trade_record.id

                        # Create a PositionRecord and link it to the Trade (if needed, for now separate)
                        position_record = PositionRecord(
                            symbol=trade_signal.symbol,
                            quantity=quantity if trade_signal.action == "BUY" else -quantity,
                            avg_entry_price=filled_avg_price,
                            entry_timestamp=datetime.datetime.now(),
                            status="OPEN"
                        )
                        session.add(position_record)
                        session.commit()
                        logging.info(f"ExecutionService: Recorded new OPEN trade: {trade_record}")
                        logging.info(f"ExecutionService: Recorded new OPEN position in DB: {position_record}")
                else:
                    logging.warning(f"ExecutionService: Order for {trade_signal.symbol} not filled or failed.")

                self.execution_request_queue.task_done()
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
