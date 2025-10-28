import xml.etree.ElementTree as ET
import logging
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def parse_ibkr_news_xml(xml_content: str) -> list[str]:
    """
    Parses the IBKR news XML content and extracts ticker symbols.
    This is a placeholder implementation and may need adjustment based on actual IBKR news XML structure.
    """
    tickers = []
    try:
        root = ET.fromstring(xml_content)

        # Common places to find tickers in news XML:
        # 1. Direct <ticker> tags
        for ticker_elem in root.findall('.//ticker'):
            if ticker_elem.text:
                tickers.append(ticker_elem.text.strip())

        # 2. Tickers as attributes (e.g., <article symbol="SPY">)
        # This is a generic check, specific tag/attribute names might be needed
        for elem in root.iter():
            if 'symbol' in elem.attrib:
                symbols = elem.attrib['symbol'].split(',') # Assuming comma-separated symbols
                for s in symbols:
                    if s.strip():
                        tickers.append(s.strip())

        # Remove duplicates and return
        return list(set(tickers))

    except ET.ParseError as e:
        logging.error(f"Failed to parse news XML: {e}")
        return []
    except Exception as e:
        logging.error(f"An unexpected error occurred during XML parsing: {e}")
        return []

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculates the Average True Range (ATR).
    Requires DataFrame with 'high', 'low', 'close' columns.
    """
    if not all(col in df.columns for col in ['high', 'low', 'close']):
        raise ValueError("DataFrame must contain 'high', 'low', and 'close' columns for ATR calculation.")

    high_low = df['high'] - df['low']
    high_prev_close = np.abs(df['high'] - df['close'].shift())
    low_prev_close = np.abs(df['low'] - df['close'].shift())

    true_range = pd.DataFrame({'hl': high_low, 'hpc': high_prev_close, 'lpc': low_prev_close}).max(axis=1)
    atr = true_range.ewm(span=period, adjust=False).mean()
    return atr

def calculate_sma(series: pd.Series, period: int) -> pd.Series:
    """
    Calculates the Simple Moving Average (SMA).
    """
    return series.rolling(window=period).mean()