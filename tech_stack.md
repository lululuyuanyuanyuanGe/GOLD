### **Technical Design & Architecture: "Momentum API" Trading Bot (Official `ibapi`)**

**1. Guiding Principles & Philosophy**

*   **Asynchronous Core, Synchronous Bridge:** The main application logic will remain on the high-performance `asyncio` event loop. All communication with the IBKR API will be handled by a dedicated, synchronous `ibapi` client running in its own separate thread. A thread-safe queue system will act as the critical bridge between these two worlds.
*   **Explicit State Management:** Unlike a high-level wrapper, we are now responsible for managing all state manually. This includes tracking request IDs, correlating responses to requests, and managing connection status explicitly within our code.
*   **Event-Driven via Queues:** The application will remain event-driven. The `EWrapper` callbacks will act as "producers," placing incoming IBKR data (news, order fills, market data) onto a queue. The `asyncio` part of our application will act as the "consumer" of this queue.
*   **Absolute Robustness:** The design prioritizes stability and direct control. By using the official library, we eliminate intermediate dependencies and ensure we are working directly against the supported source.
*   **Modularity & Separation of Concerns:** The synchronous IBKR communication layer will be strictly isolated from the asynchronous trading logic to manage complexity and improve testability.

**2. Core Technology Stack**

*   **Programming Language:** **Python 3.10+**
    *   *Justification:* `asyncio` remains the core of the application logic.
*   **IBKR API Connectivity:** **Official IBKR Python API (`ibapi`)**
    *   *Justification:* This is the officially supported, low-level library from Interactive Brokers. It provides maximum control and stability and is proven to work for the free news feeds. It consists of the `EClient` and `EWrapper` classes.
*   **Sync/Async Bridge:** **Python's `threading` and `queue` Libraries**
    *   *Justification:* These standard libraries are essential for managing the API thread and creating the thread-safe queue used to pass messages from the synchronous `EWrapper` callbacks to the main `asyncio` event loop.
*   **Asynchronous HTTP:** **`aiohttp` Library**
    *   *Justification:* Required for performing non-blocking HTTP requests to external services, such as the AI parsing API, ensuring the main event loop is never blocked by network I/O.
*   **Data Analysis & Indicators:** **NumPy & Pandas**
    *   *Justification:* Unchanged. Still the best tools for numerical and time-series analysis.
*   **Data Persistence (Trade Records):** **SQLite**
    *   *Justification:* Unchanged. A robust, serverless database for transactional trade logging.
*   **Configuration:** **YAML (`PyYAML` library)**
    *   *Justification:* Unchanged. Ideal for managing complex configuration.
*   **Environment Management:** **Poetry**
    *   *Justification:* Unchanged. Ensures a reproducible and stable environment.

**3. System Architecture & Data Flow**

The architecture is now a hybrid model with a clear boundary between the synchronous API thread and the asynchronous main application.

**(Diagram of Data Flow)**

| **Synchronous API Thread** | **The Bridge** | **Asynchronous Main Thread (Event Loop)** |
| :--- | :--- | :--- |
| `IBKR Wrapper (EWrapper)` -> | `Thread-Safe Incoming Queue` -> | `[Dispatcher Task]` -> `(Resolves Futures)` |
| `IBKR Client (EClient)` <- | *(Direct API Calls)* <- | `[Services: News, Detection, etc.]` |

**4. Detailed Component Breakdown**

*   **`IBKRBridge` (The New Core)**
    *   **Responsibility:** This is the most complex module. It encapsulates all direct interaction with the `ibapi` library and manages the API thread.
    *   **Implementation Details:**
        *   It will contain two main classes: `IBWrapper(EWrapper)` and `IBClient(EClient)`.
        *   **The Wrapper (`IBWrapper`):**
            *   It will subclass `EWrapper` and implement all necessary callback methods (`newsArticle`, `orderStatus`, `tickPrice`, `error`, etc.).
            *   The *sole job* of these callback methods is to take the incoming data, wrap it in a simple data object, and put it onto a standard, thread-safe `queue.Queue` (the "Incoming Queue").
        *   **The Client (`IBClient`):**
            *   It will subclass `EClient`.
            *   The `IBKRBridge` will start the client's standard, blocking `run()` method in a **separate `threading.Thread`**. This loop handles all low-level socket communication.
        *   **Thread Management:** The bridge is responsible for starting, monitoring, and gracefully shutting down this API thread.
        *   **Request Handling:** Asynchronous methods in the bridge (e.g., `fetch_historical_data`) now make direct, thread-safe calls to the `IBClient` instance (e.g., `self.client.reqHistoricalData(...)`). The bridge uses `asyncio.Future` objects to await the corresponding response from the `incoming_queue`.

*   **`Main Orchestrator` (`main.py`)**
    *   **Responsibility:** Initializes the `asyncio` event loop and all application modules.
    *   **Implementation Details:**
        *   It will instantiate the `IBKRBridge` and start it.
        *   It creates and runs the primary services (NewsHandler, DetectionEngine, etc.).
        *   The `IBKRBridge` internally runs a dispatcher task that bridges the gap between the sync and async worlds. This task's job is to pull items from the `IBKRBridge`'s "Incoming Queue" and route them to the correct async handlers or resolve pending `Future` objects.

*   **`NewsHandler` (Now a Consumer)**
    *   **Responsibility:** Processes news objects received from the `IBKRBridge`.
    *   **Implementation Details:**
        *   The main orchestrator will pass news objects (delivered via the `news_handler_callback` in the bridge) to this handler.
        *   Upon receiving a news object, it parses the XML and puts the ticker into the internal `asyncio.Queue` for the worker pool.

*   **`DetectionEngine` (Consumer Worker Pool)**
    *   **Responsibility:** Unchanged. Consumes tickers from the internal `asyncio.Queue`.
    *   **Implementation Details:**
        *   When it needs market data, it will now call the appropriate asynchronous method on the `IBKRBridge` instance (e.g., `await bridge.fetch_historical_data(...)`), which handles making the direct API call and returning the result.

*   **`ExecutionService`**
    *   **Responsibility:** Manages the logic for entering a trade.
    *   **Implementation Details:**
        *   It will call the appropriate method on the `IBKRBridge` instance (e.g., `bridge.place_order(...)`), passing the `Contract` and `Order` objects directly.

**5. Project Directory Structure**

The structure is updated to reflect the new bridge architecture.

```
momentum_api_bot/
├── config/
│   └── config.yaml
├── data/
│   └── trades.db
├── logs/
│   └── bot.log
├── momentum_bot/
│   ├── __init__.py
│   ├── main.py                 # Main asyncio entry point, orchestrator
│   ├── ibkr_bridge/
│   │   ├── __init__.py
│   │   ├── bridge.py           # Manages the thread, queues, and client/wrapper
│   │   ├── wrapper.py          # The EWrapper implementation
│   │   └── client.py           # The EClient implementation
│   ├── services/
│   │   ├── __init__.py
│   │   ├── news_handler.py
│   │   ├── detection_engine.py
│   │   ├── execution_service.py
│   │   └── position_manager.py
│   ├── models.py
│   └── utils.py
├── tests/
├── poetry.lock
├── pyproject.toml
└── README.md
```

### System Architecture Summary

The application is an event-driven, asynchronous system designed as a **decoupled processing pipeline**. It uses a hybrid concurrency model to safely interface with the synchronous Interactive Brokers API.

**1. Core Concurrency Model:**
    *   **Main Application:** Runs on a single thread using `asyncio` for high-performance, non-blocking I/O operations.
    *   **IBKR API Interface:** The official `ibapi` library runs in its own dedicated background `threading.Thread` to prevent blocking the main application.

**2. Communication and Data Flow:**
    *   **Bridge-to-App:** A thread-safe `queue.Queue` is used as a bridge to pass incoming messages (market data, order statuses, news) from the API thread to the main `asyncio` application.
    *   **Inter-Service Communication:** A series of `asyncio.Queue`s form a producer-consumer pipeline, passing data between internal components. This ensures non-blocking, decoupled processing.

**3. Component Pipeline:**
    *   **IBKR Bridge:** Manages the API thread and queues. Provides a high-level `async` interface for all IBKR interactions.
    *   **News Handler:** Consumes raw news from the Bridge, processes it, and places structured news objects onto the next queue.
    *   **Detection Engine:** Consumes structured news, applies the core "shock detection" logic, and produces `TradeSignal` objects onto the next queue.
    *   **Execution Service:** Consumes `TradeSignal`s, converts them into valid IBKR orders, and uses the Bridge to send them.
    *   **Position Manager:** A stateful service that monitors order statuses and account updates from the Bridge to manage the portfolio.

This architecture maximizes performance by keeping the main thread non-blocked, ensures stability by isolating components, and is scalable for future enhancements.