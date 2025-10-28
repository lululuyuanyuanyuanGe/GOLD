### **Technical Design & Architecture: "Momentum API" Trading Bot (IBKR Single-API)**

**1. Guiding Principles & Philosophy**

*   **Asynchronous-First:** The system's core is built on Python's `asyncio` event loop. This allows for efficient, non-blocking management of all simultaneous I/O operations (news stream, real-time market data subscriptions, order status updates) through a single API connection.
*   **Event-Driven & Decoupled:** The architecture follows a producer-consumer pattern. A lightweight news handler (producer) places tickers into a central queue, completely decoupling the high-speed ingestion of news from the more complex analysis and trading logic (consumers).
*   **Stateful & Resilient:** The central `IBKRConnector` module is designed as a robust state machine. It is solely responsible for managing the connection's lifecycle, including automatically recovering from the daily IBKR Gateway logoff, ensuring the rest of the application remains stable and aware of the connection's status.
*   **Fail-Safe by Design:** The system is architected for capital preservation. Gating logic is implemented at the trade execution layer, preventing any new orders from being placed unless the IBKR connection is in a fully `OPERATIONAL` state.
*   **Modularity & Testability:** Each distinct function (connection management, news processing, trade execution, position management) is encapsulated in its own module with a clearly defined responsibility, allowing for independent development and unit testing.

**2. Core Technology Stack**

*   **Programming Language:** **Python 3.10+**
    *   *Justification:* Its mature `asyncio` library is the foundation of the project. The rich ecosystem of libraries for finance, data, and API integration makes it the optimal choice.
*   **IBKR API Connectivity:** **ib_insync Library**
    *   *Justification:* A high-level, async-native Python library that provides a robust, event-driven interface to the IBKR API. It expertly handles connection management, data parsing, and callback registrations, which are critical for this project.
*   **Data Analysis & Indicators:** **NumPy & Pandas**
    *   *Justification:* NumPy provides the high-performance numerical arrays that underpin financial calculations. Pandas is used for managing the time-series data (candles) required to calculate indicators like ATR and SMA efficiently and accurately.
*   **Data Persistence (Trade Records):** **SQLite**
    *   *Justification:* A serverless, file-based SQL database engine built into Python. It provides a robust, queryable, and transaction-safe way to log every trade and its state, which is vastly superior to fragile CSV files.
*   **Configuration:** **YAML (`PyYAML` library)**
    *   *Justification:* YAML's human-readable, hierarchical structure is ideal for managing the numerous configuration parameters of the bot (API keys, strategy parameters, risk settings, etc.).
*   **Environment Management:** **Poetry**
    *   *Justification:* A modern dependency and environment management tool for Python. It ensures reproducible builds and isolates the project's dependencies, which is critical for stable deployment.

**3. System Architecture & Data Flow**

The application is a single, long-running asynchronous process. All external communication flows through a central, resilient IBKR Connector. News processing is decoupled via an async queue.

**(Diagram of Data Flow)**

`IBKR API` <--> `[IBKR Connector]` <--> `[News Handler (Producer)]` -> `[Asyncio Queue]`
    ^                   |                                              |
    | (Data Req/Resp)   | (Order Flow)                                 v
    |                   v                                              |
    `[Execution Svc]` <- `[Worker Pool (Consumers)]` -> `[Position Mgr]`

**4. Detailed Component Breakdown**

*   **`IBKRConnector` (The Central Hub & State Machine)**
    *   **Responsibility:** Manages the entire lifecycle of the connection to the IBKR Gateway. It is a state machine (`DISCONNECTED`, `CONNECTING`, `OPERATIONAL`) and acts as the single gateway for **all** API interactions.
    *   **Implementation Details:**
        *   Handles initial connection and authentication.
        *   Listens for the `disconnected` event to proactively detect the daily logoff.
        *   Implements an exponential backoff reconnection loop.
        *   Upon reconnection, it performs a state synchronization checklist (re-subscribes to all data, reconciles positions/orders) before transitioning to `OPERATIONAL`.
        *   Exposes a clean async interface for other modules: `subscribe_to_news()`, `fetch_candles(ticker)`, `stream_quotes(ticker)`, `place_order(order)`.
        *   Provides a simple `is_operational()` method for gating logic.

*   **`NewsHandler` (The Producer)**
    *   **Responsibility:** Subscribes to the IBKR news feed and places tickers into a central queue. It is designed to be extremely fast and non-blocking.
    *   **Implementation Details:**
        *   Uses the `ib_insync` `newsArticle` event handler provided by the `IBKRConnector`.
        *   Performs a minimal XML parse to extract only the ticker(s).
        *   Immediately puts the ticker into the `asyncio.Queue` shared with the worker pool.

*   **`DetectionEngine` (The Consumer Worker Pool)**
    *   **Responsibility:** A fixed pool of asynchronous tasks that consume tickers from the queue and perform the shock detection logic.
    *   **Implementation Details:**
        *   The number of workers is configurable in `config.yaml`.
        *   Each worker runs an infinite loop, awaiting a ticker from the `asyncio.Queue`.
        *   Upon receiving a ticker, it calls the `IBKRConnector` to fetch the required market data (historical candles and real-time updates).
        *   It applies the Shock Detection Algorithm.
        *   If a trade is warranted, it creates a `TradeSignal` data object and passes it to the `ExecutionService`.

*   **`ExecutionService`**
    *   **Responsibility:** Manages the logic for entering a trade.
    *   **Implementation Details:**
        *   Receives `TradeSignal` objects.
        *   **Gating Logic:** Its first action is to check `if not ibkr_connector.is_operational(): return`.
        *   Calls the Position Sizing Algorithm to get the share quantity.
        *   Constructs and transmits the Market Order via the `IBKRConnector`.
        *   Awaits the fill confirmation and writes the new "OPEN" trade to the SQLite database.

*   **`PositionManager`**
    *   **Responsibility:** Monitors all open positions and manages exits.
    *   **Implementation Details:**
        *   Periodically queries the `IBKRConnector` for the list of current positions.
        *   For each open position, it uses the `IBKRConnector` to stream real-time prices.
        *   It calculates P&L in real-time.
        *   If an exit condition (Take Profit, Stop Loss, Time Stop) is met, it calls the `ExecutionService` to close the position.

**5. Project Directory Structure**

```
momentum_api_bot/
├── config/
│   └── config.yaml           # Strategy parameters, API keys, worker count
├── data/
│   └── trades.db             # SQLite database for all trade records
├── logs/
│   └── bot.log               # Main application log file (rotating)
├── momentum_bot/
│   ├── __init__.py
│   ├── main.py               # Application entry point, orchestrator
│   ├── ibkr_connector.py     # The central state machine for all IBKR comms
│   ├── services/
│   │   ├── __init__.py
│   │   ├── news_handler.py   # The Producer
│   │   ├── detection_engine.py# The Consumer workers
│   │   ├── execution_service.py # Gated order placement
│   │   └── position_manager.py # Position monitoring and exit logic
│   ├── models.py             # Dataclasses for TradeSignal, Position, etc.
│   └── utils.py              # Helper functions (e.g., XML parser)
├── tests/
│   └── ...                   # Unit and integration tests
├── poetry.lock
├── pyproject.toml            # Project dependencies defined for Poetry
└── README.md
```