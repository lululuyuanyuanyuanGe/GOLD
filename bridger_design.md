### The Core Concept: A Central Request Registry

The `IBKRBridge` will maintain a central, thread-safe dictionary that acts as a registry for all pending requests. This registry will be the "brain" that connects outgoing requests to incoming responses.

*   **The Key:** The `reqId`.
*   **The Value:** A `RequestContext` object containing everything needed to handle the response.

### Component 1: The Thread-Safe Request ID Generator

We need a mechanism that can safely provide a new, unique `reqId` every time any part of our system needs one, without any risk of two components getting the same ID.

*   **Implementation:** A simple integer counter protected by a `threading.Lock`.
*   **Location:** This will be a small, private utility within the `IBKRBridge`.

```python
# In IBKRBridge...
self._next_req_id = 0
self._req_id_lock = threading.Lock()

def get_next_req_id(self) -> int:
    with self._req_id_lock:
        self._next_req_id += 1
        return self._next_req_id
```

### Component 2: The `RequestContext` Model

This is a simple data structure (like a `dataclass`) that holds the "context" for a single pending request.

```python
# In a models.py file...
@dataclass
class RequestContext:
    reqId: int
    request_details: dict  # e.g., {'ticker': 'AAPL', 'type': 'MKT_DATA'}
    future: asyncio.Future # The magic component!
```
*   **`future: asyncio.Future`:** This is the key insight from `ib_insync`. An `asyncio.Future` is a placeholder object, a "promise" that a result will be put into it later. Our `asyncio` code can `await` this future, and it will pause until some other part of the system (even from another thread) puts a result in it.

### Component 3: The Central Registry and Dispatcher

*   **The Registry:** A simple dictionary in the `IBKRBridge`: `self._pending_requests = {}`.
*   **The Dispatcher:** This is the logic in our `asyncio` application that reads from the "Incoming Queue," looks up the `reqId` in the registry, and resolves the correct `Future`.

---

### The End-to-End Workflow: Tracing a Single Request

Let's trace a market data request from a `DetectionEngine` worker to see how all the pieces fit together.

**Step 1: The Request (Async Main Thread)**

1.  A worker needs market data for "TSLA". It **does not** call `EClient` directly. Instead, it calls a high-level, async method on our `IBKRBridge`.

    ```python
    # Inside a DetectionEngine worker...
    market_data = await self.ibkr_bridge.fetch_market_data("TSLA")
    ```

2.  The `fetch_market_data` method inside the `IBKRBridge` does the following:
    *   Gets a new, unique ID: `req_id = self.get_next_req_id()` (e.g., `101`).
    *   Creates an `asyncio.Future`: `future = asyncio.get_running_loop().create_future()`.
    *   Creates the context: `context = RequestContext(reqId=101, request_details={'ticker': 'TSLA'}, future=future)`.
    *   **Registers the context:** `self._pending_requests[101] = context`.
    *   Creates the raw request for the API thread: `raw_request = {'type': 'REQ_MKT_DATA', 'reqId': 101, 'ticker': 'TSLA'}`.
    *   Puts the raw request onto the **"Outgoing Queue"** for the API thread to process.
    *   **Returns the future to the worker:** `return await future`. The worker's code now pauses here, waiting for this future to be resolved.

**Step 2: The Execution (Sync API Thread)**

1.  The dedicated API thread's loop gets the `raw_request` from the "Outgoing Queue".
2.  It constructs the `Contract` object for "TSLA".
3.  It calls the low-level `EClient` method: `self.client.reqMktData(reqId=101, contract=tsla_contract, ...)`.

**Step 3: The Response (Sync `EWrapper` Callback)**

1.  A few moments later, the IBKR server sends back a price. The API thread automatically calls our `EWrapper` method.
2.  `def tickPrice(self, reqId, tickType, price, attrib):` is executed.
3.  The **only thing** this method does is package the data and put it on the **"Incoming Queue"** for the `asyncio` thread to handle safely.
    *   `incoming_message = {'type': 'TICK_PRICE', 'reqId': reqId, 'data': {'price': price}}`
    *   `self.incoming_queue.put(incoming_message)`

**Step 4: The Dispatch and Resolution (Async Main Thread)**

1.  A central "Dispatcher" task in our `asyncio` main loop is constantly pulling from the "Incoming Queue". It gets the `incoming_message`.
2.  It extracts the `reqId`: `req_id = incoming_message['reqId']` (which is `101`).
3.  It looks up the ID in our registry: `context = self._pending_requests.pop(101)`. We use `.pop()` to remove it as it's now being handled.
4.  It gets the `Future` object from the context: `future = context.future`.
5.  **It resolves the future with the data:** `future.set_result(incoming_message['data'])`.

**Step 5: The Worker Wakes Up**

1.  The `set_result()` call immediately "wakes up" the original `DetectionEngine` worker that was paused at `await future`.
2.  The `market_data` variable in the worker is now assigned the value `{'price': ...}`.
3.  The worker continues its execution with the data it needed.

### Summary of Benefits of This Design

*   **Complete Abstraction:** The rest of the application never sees or thinks about a `reqId`.
*   **Thread-Safety:** The queues provide a safe, unbreakable boundary between the synchronous API thread and the asynchronous main application.
*   **Clear State Management:** The `_pending_requests` registry is the single source of truth for what the application is waiting for.
*   **Scalability:** This pattern works perfectly with our pool of consumer workers. Each worker can make a request, get its own unique `Future`, and await its own specific result without interfering with any other worker.
*   **Error Handling:** We can add timeouts to our `RequestContext` and have a cleanup task that cancels futures and logs errors for requests that never get a response.

This is a robust, production-grade implementation of the pattern `ib_insync` uses, tailored specifically for our hybrid thread/async architecture. It is the definitive solution to the `reqId` management problem.