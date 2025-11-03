### For some infrequeently invoked request like request new providers etc. We will use a fixed request id for them.
IBKR will send all non data message through error channel, hence we need to carefully check the error code to decide if it is an actual error or not。

### Debugging and Fixing the Benzinga News Feed Subscription

**Problem:** The application was unable to subscribe to the Benzinga (`BZ`) news feed. Initial attempts resulted in a `321 - The entered news source is invalid` error from the IBKR API, even though the logs showed the correct provider code (`BZ`) was being sent. The error message itself was confusing, referencing an unknown `'bP'` source.

**Solution:** The issue was traced to two incorrect implementations in the news subscription and handling mechanism. The fix involved a multi-step debugging process:

1.  **Correcting the `EWrapper` Callback:** The initial implementation incorrectly used the `tickString` callback with `tickType 47` (Fundamental Ratios) to listen for news. This was wrong. The code was refactored to use the correct, dedicated `tickNews` callback in `ibkr_bridge/wrapper.py`. This ensures that incoming news headlines are properly captured.

2.  **Fixing the `reqMktData` Call:** After implementing the correct callback, news was still not being received. The root cause was found in the `reqMktData` call within `ibkr_bridge/bridge.py`. The `genericTickList` parameter, which tells the API what kind of data to send, was being passed as an empty string.

    The call was corrected to include `"292"`, which is the specific generic tick type for news headlines.

    *   **Contract Symbol:** Set to `f"{provider_code}:{provider_code}_ALL"` (e.g., `"BZ:BZ_ALL"`) for a broad-tape feed.
    *   **Contract Exchange:** Set to the `provider_code` (e.g., `"BZ"`).
    *   **Generic Tick List:** Set to `"292"`.

**Benefit:** With the correct `reqMktData` parameters and the `tickNews` callback properly implemented, the application now successfully subscribes to and receives real-time news headlines from the Benzinga feed, resolving a critical data-sourcing issue.

The entire system will be an event driven system that

### Architectural Refactor: "Queue as Interface" for Inter-Service Communication

**Problem:** There was a design mismatch between the `IBKRBridge` (which used a direct callback to "push" news) and the `NewsHandler` (which was designed to "pull" news from a queue). This created a tight coupling and an inconsistent data flow.

**Solution:** Refactored the entire application to use a consistent, event-driven "Queue as Interface" pattern for all communication between services. This aligns with the core design principles.

**Implementation:**
1.  **`IBKRBridge` as Producer:** The bridge no longer uses a direct callback. It now acts as a simple producer, placing the raw news data dictionary onto a dedicated `raw_news_queue`.
2.  **`NewsHandler` as Consumer:** The handler was refactored to consume from the `raw_news_queue`, process the data, and place the results onto a `processed_news_queue` for the next service in the pipeline.
3.  **`main.py` as Orchestrator:** The main application entry point was overhauled to create and connect these queues, wiring all the services together. The startup and shutdown logic was also modernized and made more robust.

**Benefit:** This architecture is now fully non-blocking, truly decoupled, and provides a clear, scalable data pipeline for handling high-frequency events. 