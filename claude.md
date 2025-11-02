# Claude Project Overview: "Momentum API" Real-Time News Trading Bot

This document provides a synthesized overview of the "Momentum API" project, based on the information from `gemini.md`, `prd(api).md`, `development_progress.md`, and `development_log.md`.

## 1. Introduction & Vision

**The Problem:** Financial markets price in new information with extreme velocity. Manually trading on breaking news is impossible due to the speed required to ingest, analyze, and act. An automated solution is required to systematically capture the initial price movement driven by significant news events.

**The Vision:** To create a high-speed, automated trading system that connects directly to a low-latency news feed via the **Interactive Brokers (IBKR) API**. The system will programmatically identify news tied to a specific stock, analyze its market data for a reaction, execute a trade in the direction of the momentum, and manage the position based on a strict set of rules.

## 2. Core Workflow

1.  Establish a persistent, resilient connection to the **IBKR API**.
2.  Subscribe to a real-time, machine-readable news feed (e.g., Benzinga) through the **IBKR API**.
3.  Instantly parse incoming news data to extract the stock ticker, now using an AI-based service for robustness.
4.  Upon receiving a ticker, analyze live market data from the **IBKR API** for a qualifying price/volume "shock."
5.  Execute a market order to enter a position and apply a predefined risk management strategy to exit, all via the **IBKR API**.

## 3. System Architecture

The application is a single, long-running asynchronous process built on an **event-driven and decoupled** architecture.

```
IBKR API <--> [IBKR Bridge] -> (raw_news_queue) -> [NewsHandler] -> (processed_news_queue) -> [DetectionEngine] -> ...
```

**Key Architectural Principles:**

*   **Asynchronous-First:** The core of the application is built on Python's `asyncio` event loop for high-performance, non-blocking I/O.
*   **"Queue as Interface":** All communication between services is standardized through `asyncio.Queue`s. This creates a fully decoupled, non-blocking processing pipeline where each service acts as a producer, a consumer, or both.
*   **Resilient IBKR Bridge:** A central `IBKRBridge` module manages the connection to the synchronous official `ibapi` library in a dedicated thread. It uses thread-safe queues to pass incoming messages (like news or market data) from the API thread to the main `asyncio` application thread, ensuring seamless and safe communication.

## 4. Key Modules & Features

The system is composed of several distinct services that communicate via queues:

*   **IBKR Bridge:** Manages the API connection state (`DISCONNECTED`, `CONNECTING`, `OPERATIONAL`) and handles automatic reconnection. It has been refactored to use the official `ibapi` library for improved stability and control.
*   **News Handler:** Consumes raw news items from the bridge. It has been upgraded from a simple XML parser to use a dedicated AI service (`extract_symbols_with_ai` via `aiohttp`) for robustly extracting ticker symbols from structured and unstructured news text.
*   **Detection Engine:** Receives tickers and requests real-time market data from IBKR. It applies a configurable "Shock Detection Algorithm" to qualify tradeable events and generates a `TradeSignal`.
*   **Execution Service:** Acts on `TradeSignal`s. It calculates the appropriate position size using the "Position Sizing Algorithm," checks that the IBKR connection is `OPERATIONAL`, places market orders, and records the new position in the database.
*   **Position Manager:** Monitors open positions using real-time IBKR market data, calculates P&L, and implements exit rules (Take-Profit, Stop-Loss, Max Time in Trade), updating the database upon closing a trade.

## 5. Core Technology Stack

*   **Programming Language:** **Python 3.10+** (with `asyncio` for concurrency)
*   **IBKR API Connectivity:** **IBKR official `ibapi` Library**
*   **AI-based Parsing:** **aiohttp** (for asynchronous API calls to the parsing service)
*   **Data Analysis & Indicators:** **NumPy & Pandas**
*   **Data Persistence:** **SQLite** (via SQLAlchemy for trade and position records)
*   **Configuration:** **YAML (`PyYAML` library)**
*   **Environment Management:** **Poetry**

## 6. Algorithms

### 6.1. Shock Detection Algorithm

Confirms a tradeable event if **both** price and volume shocks are detected in the most recent 1-minute candle.

*   **Price Shock:** `(|Close - Open| / Open) > (ATR(10) / Open) * Price_Multiplier` (Default Multiplier: 3.0)
*   **Volume Shock:** `Current_Volume > SMA(Volume, 20) * Volume_Multiplier` (Default Multiplier: 5.0)

### 6.2. Position Sizing Algorithm

Calculates share size using a Fixed Fractional risk model.

*   **Formula:** `Position_Size_in_Shares = floor((Account_Value * Risk_Per_Trade_%) / (|Entry_Price - Stop_Loss_Price|))`
*   **Default Risk:** 1.0% of account value per trade.

## 7. Development Progress Summary

*   **Architectural Overhaul:** The project was significantly refactored from using `ib_insync` to the official `ibapi` library, leading to the creation of the robust, threaded `IBKRBridge`.
*   **Event-Driven Pipeline:** The entire data flow was redesigned to use a consistent "Queue as Interface" pattern, fully decoupling all services.
*   **AI-Powered Parsing:** A simple XML parser was replaced with a call to an external AI service, making news parsing more intelligent and resilient to format changes.
*   **Database Integration:** SQLite was integrated using SQLAlchemy to persist all trade and position records, allowing for state recovery and analysis.

## 8. Next Steps & Critical Risks

### Next Steps

1.  **Testing and Validation:** Implement comprehensive unit and integration tests.
2.  **Configuration Management:** Externalize all magic numbers and strategy parameters into `config/config.yaml`.
3.  **Error Handling and Robustness:** Enhance error handling, logging, and edge-case management.

### Critical Risks

*   **Latency Disadvantage (HIGH):** Competition with institutional firms may result in suboptimal entry prices.
*   **Execution Risk (HIGH):** Trading during high-volatility moments exposes market orders to significant **slippage** and wide spreads.
*   **Single Point of Failure (MEDIUM):** The entire operation depends on the uptime and performance of the IBKR API.

## 9. How to Build and Run

1.  **Install Dependencies:**
    ```bash
    uv pip install -e .
    ```

2.  **Run the Application:**
    Ensure the IBKR TWS or Gateway is running and configured for API connections.
    ```bash
    D:\\proejects\\Gold\\.venv\\Scripts\\python.exe -m momentum_api_bot.momentum_bot.main
    ```
