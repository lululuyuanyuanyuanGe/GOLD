import asyncio
import logging
import pandas as pd
import numpy as np
from ib_insync import Contract
from momentum_bot.ibkr_connector import IBKRConnector
from momentum_bot.models import TradeSignal
from momentum_bot.utils import calculate_atr, calculate_sma

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DetectionEngine:
    def __init__(self, ibkr_connector: IBKRConnector, news_queue: asyncio.Queue, execution_queue: asyncio.Queue, num_workers: int = 5):
        self.ibkr_connector = ibkr_connector
        self.news_queue = news_queue
        self.execution_queue = execution_queue
        self.num_workers = num_workers
        self.workers = []
        logging.info(f"DetectionEngine initialized with {num_workers} workers.")

    async def start(self):
        logging.info("Starting DetectionEngine workers...")
        for i in range(self.num_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i+1}"))
            self.workers.append(worker)
        # await asyncio.gather(*self.workers) # Don't gather here, let them run indefinitely

    async def _worker(self, worker_id: str):
        logging.info(f"DetectionEngine {worker_id} started.")
        while True:
            try:
                ticker = await self.news_queue.get()
                logging.info(f"DetectionEngine {worker_id}: Received ticker {ticker} from news queue.")

                if not self.ibkr_connector.is_operational():
                    logging.warning(f"DetectionEngine {worker_id}: IBKR connector not operational. Skipping {ticker}.")
                    self.news_queue.task_done()
                    continue

                # Fetch historical data for ATR/SMA calculation
                logging.info(f"DetectionEngine {worker_id}: Fetching historical data for {ticker}.")
                contract = Contract(symbol=ticker, secType='STK', exchange='SMART', currency='USD')
                # Fetch enough data for ATR(10) and SMA(20) - e.g., 30 bars of 1 minute
                bars = await self.ibkr_connector.fetch_candles(contract, durationStr='30 T', barSizeSetting='1 min')

                if not bars:
                    logging.warning(f"DetectionEngine {worker_id}: No historical data for {ticker}. Skipping shock detection.")
                    self.news_queue.task_done()
                    continue

                # Convert bars to pandas DataFrame
                df = pd.DataFrame([(b.date, b.open, b.high, b.low, b.close, b.volume) for b in bars],
                                  columns=['date', 'open', 'high', 'low', 'close', 'volume'])
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')

                # Ensure enough data for calculations
                if len(df) < 20: # Need at least 20 for SMA(20)
                    logging.warning(f"DetectionEngine {worker_id}: Not enough historical data for {ticker} ({len(df)} bars). Skipping shock detection.")
                    self.news_queue.task_done()
                    continue

                # Calculate ATR(10)
                atr_10 = calculate_atr(df, period=10).iloc[-1] # Get the latest ATR
                if pd.isna(atr_10) or atr_10 == 0:
                    logging.warning(f"DetectionEngine {worker_id}: ATR(10) is invalid or zero for {ticker}. Skipping shock detection.")
                    self.news_queue.task_done()
                    continue

                # Calculate SMA(Volume, 20)
                sma_volume_20 = calculate_sma(df['volume'], period=20).iloc[-1] # Get the latest SMA
                if pd.isna(sma_volume_20) or sma_volume_20 == 0:
                    logging.warning(f"DetectionEngine {worker_id}: SMA(Volume, 20) is invalid or zero for {ticker}. Skipping shock detection.")
                    self.news_queue.task_done()
                    continue

                # Get current 1-minute candle data (last bar in historical data)
                current_bar = df.iloc[-1]
                current_open = current_bar['open']
                current_close = current_bar['close']
                current_volume = current_bar['volume']

                # Stream real-time quotes to get the most up-to-date price and volume
                logging.info(f"DetectionEngine {worker_id}: Streaming real-time quotes for {ticker}.")
                realtime_ticker = await self.ibkr_connector.stream_quotes(contract)

                if realtime_ticker and realtime_ticker.last != realtime_ticker.last: # Check for NaN
                    current_close = realtime_ticker.last
                    # IBKR real-time volume is cumulative, so we need to calculate volume for the current bar
                    # This is a simplification; a more robust solution would track volume per minute.
                    # For now, we'll just use the last historical bar's volume as a base and add a small simulated increment.
                    current_volume = current_bar['volume'] + (realtime_ticker.volume if realtime_ticker.volume else 0)
                    logging.info(f"DetectionEngine {worker_id}: Real-time update for {ticker}: Close={current_close}, Volume={current_volume}")

                price_multiplier = 3.0 # From PRD
                volume_multiplier = 5.0 # From PRD

                # Condition 1: Price Shock. (|Close - Open| / Open) > (ATR(10) / Open) * Price_Multiplier
                price_shock_condition = False
                if current_open != 0: # Avoid division by zero
                    price_shock_condition = abs(current_close - current_open) / current_open > (atr_10 / current_open) * price_multiplier

                # Condition 2: Volume Shock. Current_Volume > SMA(Volume, 20) * Volume_Multiplier
                volume_shock_condition = current_volume > sma_volume_20 * volume_multiplier

                is_shock_detected = price_shock_condition and volume_shock_condition
                logging.info(f"DetectionEngine {worker_id}: {ticker} - Price Shock: {price_shock_condition}, Volume Shock: {volume_shock_condition}, ATR_10: {atr_10:.2f}, SMA_Vol_20: {sma_volume_20:.2f}, Current Vol: {current_volume}")

                if is_shock_detected:
                    logging.info(f"DetectionEngine {worker_id}: Shock detected for {ticker}. Creating TradeSignal.")
                    trade_signal = TradeSignal(
                        symbol=ticker,
                        action="BUY", # Or "SELL" based on further analysis
                        entry_price=current_close, # Use current close as entry price
                        timestamp=current_bar.name.timestamp() # Use timestamp of the bar
                    )
                    await self.execution_queue.put(trade_signal)
                    logging.info(f"DetectionEngine {worker_id}: Put TradeSignal for {ticker} into execution queue.")
                else:
                    logging.info(f"DetectionEngine {worker_id}: No shock detected for {ticker}.")

                self.news_queue.task_done()
            except asyncio.CancelledError:
                logging.info(f"DetectionEngine {worker_id}: Worker cancelled.")
                break
            except Exception as e:
                logging.error(f"DetectionEngine {worker_id}: An error occurred: {e}", exc_info=True)

    async def stop(self):
        logging.info("Stopping DetectionEngine workers...")
        for worker in self.workers:
            worker.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)
        logging.info("DetectionEngine workers stopped.")
