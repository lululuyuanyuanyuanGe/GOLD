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
| `IBKR Wrapper (EWrapper)` -> | `Thread-Safe Incoming Queue` -> | `[News Handler]` -> `[Asyncio Queue]` |
| `IBKR Client (EClient)` <- | `Thread-Safe Outgoing Queue` <- | `[Worker Pool]` -> `[Execution Svc]` |
| | | `[Position Manager]` |

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
            *   The `IBKRBridge` will have a `run()` method that starts the client's internal event loop in a **separate `threading.Thread`**.
        *   **Thread Management:** The bridge is responsible for starting, monitoring, and gracefully shutting down this API thread.
        *   **Request Handling:** It will run a loop that pulls request objects from an "Outgoing Queue" and calls the appropriate `EClient` methods (e.g., `placeOrder`, `reqMktData`).

*   **`Main Orchestrator` (`main.py`)**
    *   **Responsibility:** Initializes the `asyncio` event loop and all application modules.
    *   **Implementation Details:**
        *   It will instantiate the `IBKRBridge` and start its thread.
        *   It will create the `asyncio.Queue` for the producer-consumer pattern.
        *   It will create and run the main consumer task that bridges the gap between the sync and async worlds. This task's job is to pull items from the `IBKRBridge`'s "Incoming Queue" and route them to the correct async handlers.

*   **`NewsHandler` (Now a Consumer)**
    *   **Responsibility:** Processes news objects received from the `IBKRBridge`.
    *   **Implementation Details:**
        *   It no longer subscribes directly.
        *   The main orchestrator will pass news objects (pulled from the Incoming Queue) to this handler.
        *   Upon receiving a news object, it parses the XML and puts the ticker into the internal `asyncio.Queue` for the worker pool.

*   **`DetectionEngine` (Consumer Worker Pool)**
    *   **Responsibility:** Unchanged. Consumes tickers from the internal `asyncio.Queue`.
    *   **Implementation Details:**
        *   When it needs market data, it will **not** call an API directly. Instead, it will create a "request" object (e.g., `{'type': 'FETCH_CANDLES', 'ticker': 'AAPL'}`) and put it onto the "Outgoing Queue" for the `IBKRBridge` to handle. It will then have to `await` a response, likely via a future/event mechanism.

*   **`ExecutionService`**
    *   **Responsibility:** Manages the logic for entering a trade.
    *   **Implementation Details:**
        *   Instead of calling `ib.place_order()`, it will construct an `Order` object and a `Contract`, wrap them in a request dictionary (e.g., `{'type': 'PLACE_ORDER', 'order': ..., 'contract': ...}`), and put it onto the "Outgoing Queue".

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