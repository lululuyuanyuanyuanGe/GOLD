from dataclasses import dataclass

@dataclass
class TradeSignal:
    symbol: str
    action: str  # e.g., 'BUY', 'SELL'
    entry_price: float
    timestamp: float
    # Add other relevant fields as needed, e.g., signal_strength, news_id

@dataclass
class Position:
    symbol: str
    quantity: int
    avg_entry_price: float
    entry_timestamp: float
    status: str # e.g., 'OPEN', 'CLOSED'
    # Add other relevant fields as needed, e.g., order_id, exit_price, exit_timestamp