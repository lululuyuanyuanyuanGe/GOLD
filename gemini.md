# Project Overview: "Momentum API" Real-Time News Trading Bot

This project is an asynchronous Python-based financial data and trading platform that leverages the Interactive Brokers (IBKR) API. It is designed to be a high-speed, automated trading system that systematically captures initial price movements driven by significant news events.

## 1. Introduction & Vision (from prd(api).md)

**1.1. The Problem:** Financial markets price in new information with extreme velocity. Manually trading on breaking news is impossible due to the speed required to ingest, analyze, and act. An automated solution is required to systematically capture the initial price movement driven by significant news events.

**1.2. The Vision:** To create a high-speed, automated trading system that connects directly to a low-latency news feed via the **Interactive Brokers (IBKR) API**. The system will programmatically identify news tied to a specific stock, analyze its market data for a reaction, execute a trade in the direction of the momentum, and manage the position based on a strict set of rules, all within the IBKR ecosystem.

**1.3. Core Workflow:**
1.  Establish a persistent, resilient connection to the **IBKR API**.
2.  Subscribe to a real-time, machine-readable news feed (e.g., Benzinga) through the **IBKR API**.
3.  Instantly parse incoming structured news data to extract the stock ticker.
4.  Upon receiving a ticker, analyze live market data, also from the **IBKR API**, for a qualifying price/volume "shock."
5.  Execute a market order to enter a position and apply a predefined risk management strategy to exit, all via the **IBKR API**.

## 2. Key Features (from prd(api).md)

The system is modular, with distinct components for connection management, news processing, event detection, trade execution, and position management.

*   **IBKR Gateway Connection:** Securely manages and utilizes IBKR API credentials, implements a robust state machine, and handles automatic reconnection with exponential backoff.
*   **Real-Time News Ingestion & Parsing:** Subscribes to designated news feeds via the IBKR API, parses structured news data (XML) to extract ticker symbols, and efficiently filters news items.
*   **Event Detection & Qualification Engine:** Receives tickers from news alerts, requests real-time market data from IBKR, and applies a configurable "Shock Detection Algorithm" to qualify tradeable events.
*   **Trade Execution & Position Sizing:** Places market orders with calculated share sizes based on trade signals, confirms order acceptance, and implements gating logic to ensure operational connection status.
*   **Position & Risk Management:** Monitors open positions using real-time IBKR market data, calculates P&L, and implements exit rules (Take-Profit, Stop-Loss, Max Time in Trade).

## 3. Core Technology Stack (from tss.md)

*   **Programming Language:** **Python 3.10+** (with `asyncio` for concurrency)
*   **IBKR API Connectivity:** **IBKR official ib gateway Library**
*   **Data Analysis & Indicators:** **NumPy & Pandas** (for numerical operations and time-series data)
*   **Data Persistence (Trade Records):** **SQLite** (serverless, file-based SQL database via SQLAlchemy)
*   **Configuration:** **YAML (`PyYAML` library)** (for human-readable configuration)
*   **Environment Management:** **Poetry** (for reproducible builds and dependency isolation)

## 4. System Architecture & Data Flow (from tss.md)

The application operates as a single, long-running asynchronous process. Communication flows through a central `IBKRBridge`, which manages a dedicated thread for the official `ibapi` library. An `asyncio.Queue` is used to pass incoming messages from the API thread to the main application thread.

```
IBKR API <--> [IBKR Bridge] -> (Incoming Queue) -> [Asyncio Services]
    ^              |
    |              `-(Direct API Calls)---- [Asyncio Services]
    `-(Market Data, Order Status, etc.)
```

## 5. Building and Running

To run the project, you need to have Python 3.10+ and the dependencies installed.

**1. Install Dependencies:**

```bash
uv pip install -e .
```

**2. Run the Application:**

Before running, ensure the Interactive Brokers Trader Workstation (TWS) or Gateway is running and configured to accept API connections.

From the project root (`D:\proejects\Gold`), execute:

```bash
D:\proejects\Gold\.venv\Scripts\python.exe -m momentum_api_bot.momentum_bot.main
```
*(Note: The `main.py` includes a `sys.path` modification to ensure `momentum_bot` is discoverable.)*

## 6. Development Conventions (from tss.md)

*   **Asynchronous-First:** Core built on Python's `asyncio` event loop.
*   **Event-Driven & Decoupled:** Producer-consumer pattern for modules.
*   **Stateful & Resilient:** `IBKRConnector` manages connection lifecycle and recovery.
*   **Fail-Safe by Design:** Gating logic prevents orders unless IBKR is `OPERATIONAL`.
*   **Modularity & Testability:** Clear separation of concerns for independent development.

## 7. Development Progress (from development_progress.md)

Refer to `development_progress.md` for a detailed summary of completed work and recent progress, including:

*   Project scaffolding and initial core module implementations.
*   Dependency management.
*   Application orchestration in `main.py`.
*   Refinement of `NewsHandler` with XML parsing.
*   Enhanced `DetectionEngine` with placeholder "Shock Detection Algorithm."
*   Implemented "Position Sizing Algorithm" in `ExecutionService`.
*   Integrated SQLite for Trade and Position Records.
*   Refined `IBKRConnector` API calls.
*   Refined `DetectionEngine` Market Data and Technical Indicators.
*   Implemented Real-time Market Data Streaming in `DetectionEngine`.
*   Refined `PositionManager` P&L Calculation.
*   Resolved various runtime errors (`ModuleNotFoundError`, `sqlalchemy.exc.OperationalError`, `AttributeError`s).

## 7. Conventions and rules in this project (from development_log.md)

### Next Steps:

*   **Testing and Validation:** Implement comprehensive unit and integration tests for all modules.
*   **Configuration Management:** Externalize all configurable parameters (e.g., IBKR connection details, strategy parameters, risk settings) into `config/config.yaml` and ensure they are properly loaded and utilized.
*   **Error Handling and Robustness:** Enhance error handling, logging, and edge-case management across all modules for increased system robustness.

## 8. Agent Rules

*   **Search Tool Usage:** Use the `google_web_search` tool to search for API usage, limitations, or any other information needed during development.
*   **Documentation Reference:** When needed, reference `prd(api).md`, `tss.md`, and `development_progress.md` for project requirements, technical design, and development progress.
