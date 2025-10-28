import asyncio
import logging
from momentum_bot.ibkr_connector import IBKRConnector
from momentum_bot.models import Position, TradeSignal
from momentum_bot.services.execution_service import ExecutionService
from momentum_bot.database import PositionRecord, Trade
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PositionManager:
    def __init__(self, ibkr_connector: IBKRConnector, execution_service: ExecutionService, Session: sessionmaker):
        self.ibkr_connector = ibkr_connector
        self.execution_service = execution_service
        self.Session = Session
        self.open_positions = {} # Dictionary to store open positions: {symbol: PositionRecord}
        self.monitor_task = None
        logging.info("PositionManager initialized.")

    async def start(self, interval: int = 5):
        logging.info(f"Starting PositionManager to monitor positions every {interval} seconds...")
        # Load existing open positions from the database
        with self.Session() as session:
            stmt = select(PositionRecord).where(PositionRecord.status == 'OPEN')
            for record in session.scalars(stmt):
                self.open_positions[record.symbol] = record
                logging.info(f"Loaded open position from DB: {record}")

        self.monitor_task = asyncio.create_task(self._monitor_positions(interval))

    async def _monitor_positions(self, interval: int):
        while True:
            try:
                await asyncio.sleep(interval)
                if not self.ibkr_connector.is_operational():
                    logging.warning("PositionManager: IBKR connector not operational. Skipping position monitoring.")
                    continue

                logging.info("PositionManager: Monitoring open positions...")
                
                # Iterate over a copy to allow modification during iteration
                for symbol, position_record in list(self.open_positions.items()):
                    logging.info(f"PositionManager: Checking position for {symbol}: {position_record}")
                    
                    # Fetch real-time market data for the open position
                    contract = Contract(symbol=symbol, secType='STK', exchange='SMART', currency='USD')
                    realtime_ticker = await self.ibkr_connector.stream_quotes(contract)

                    if not realtime_ticker or realtime_ticker.last != realtime_ticker.last: # Check for NaN
                        logging.warning(f"PositionManager: Could not get real-time price for {symbol}. Skipping P&L calculation.")
                        continue

                    current_price = realtime_ticker.last
                    pnl = (current_price - position_record.avg_entry_price) * position_record.quantity
                    logging.info(f"PositionManager: {symbol} Current Price: {current_price:.2f}, P&L: {pnl:.2f}")

                    # Placeholder for exit conditions (Take Profit, Stop Loss, Time Stop)
                    if pnl > 500: # Simulate Take Profit
                        logging.info(f"PositionManager: Take Profit hit for {symbol}. Closing position.")
                        exit_signal = TradeSignal(
                            symbol=symbol,
                            action="SELL" if position_record.quantity > 0 else "BUY",
                            entry_price=current_price,
                            timestamp=datetime.datetime.now().timestamp()
                        )
                        await self.execution_service.execution_queue.put(exit_signal)
                        
                        with self.Session() as session:
                            # Update PositionRecord status
                            db_position = session.get(PositionRecord, position_record.id)
                            if db_position:
                                db_position.status = 'CLOSED'
                                session.add(db_position)

                            # Update corresponding Trade record
                            # Assuming there's a way to link PositionRecord to Trade (e.g., via symbol and status)
                            # For simplicity, we'll find the latest OPEN trade for this symbol
                            trade_to_update = session.query(Trade).filter(
                                Trade.symbol == symbol,
                                Trade.status == 'OPEN'
                            ).order_by(Trade.entry_timestamp.desc()).first()

                            if trade_to_update:
                                trade_to_update.exit_price = current_price
                                trade_to_update.exit_timestamp = datetime.datetime.now()
                                trade_to_update.pnl = pnl
                                trade_to_update.status = 'CLOSED'
                                session.add(trade_to_update)

                            session.commit()
                            logging.info(f"PositionManager: Updated position {symbol} to CLOSED in DB and corresponding Trade record.")
                        del self.open_positions[symbol] # Remove from open positions

                    elif pnl < -200: # Simulate Stop Loss
                        logging.info(f"PositionManager: Stop Loss hit for {symbol}. Closing position.")
                        exit_signal = TradeSignal(
                            symbol=symbol,
                            action="SELL" if position_record.quantity > 0 else "BUY",
                            entry_price=current_price,
                            timestamp=datetime.datetime.now().timestamp()
                        )
                        await self.execution_service.execution_queue.put(exit_signal)
                        
                        with self.Session() as session:
                            # Update PositionRecord status
                            db_position = session.get(PositionRecord, position_record.id)
                            if db_position:
                                db_position.status = 'CLOSED'
                                session.add(db_position)

                            # Update corresponding Trade record
                            trade_to_update = session.query(Trade).filter(
                                Trade.symbol == symbol,
                                Trade.status == 'OPEN'
                            ).order_by(Trade.entry_timestamp.desc()).first()

                            if trade_to_update:
                                trade_to_update.exit_price = current_price
                                trade_to_update.exit_timestamp = datetime.datetime.now()
                                trade_to_update.pnl = pnl
                                trade_to_update.status = 'CLOSED'
                                session.add(trade_to_update)

                            session.commit()
                            logging.info(f"PositionManager: Updated position {symbol} to CLOSED in DB and corresponding Trade record.")
                        del self.open_positions[symbol] # Remove from open positions

            except asyncio.CancelledError:
                logging.info("PositionManager: Monitor task cancelled.")
                break
            except Exception as e:
                logging.error(f"PositionManager: An error occurred: {e}", exc_info=True)

    async def stop(self):
        if self.monitor_task:
            logging.info("Stopping PositionManager monitor task...")
            self.monitor_task.cancel()
            await self.monitor_task
            logging.info("PositionManager monitor task stopped.")

    def add_position(self, position: PositionRecord):
        # This method might not be needed if positions are loaded from DB at startup
        # and added to DB by ExecutionService
        self.open_positions[position.symbol] = position
        logging.info(f"PositionManager: Added new position to monitor: {position}")
