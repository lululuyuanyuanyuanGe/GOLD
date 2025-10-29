### For some infrequeently invoked request like request new providers etc. We will use a fixed request id for them.
IBKR will send all non data message through error channel, hence we need to carefully check the error code to decide if it is an actual error or not。
The entire system will be an event driven system that

### Architectural Refactor: "Queue as Interface" for Inter-Service Communication

**Problem:** There was a design mismatch between the `IBKRBridge` (which used a direct callback to "push" news) and the `NewsHandler` (which was designed to "pull" news from a queue). This created a tight coupling and an inconsistent data flow.

**Solution:** Refactored the entire application to use a consistent, event-driven "Queue as Interface" pattern for all communication between services. This aligns with the core design principles.

**Implementation:**
1.  **`IBKRBridge` as Producer:** The bridge no longer uses a direct callback. It now acts as a simple producer, placing the raw news data dictionary onto a dedicated `raw_news_queue`.
2.  **`NewsHandler` as Consumer:** The handler was refactored to consume from the `raw_news_queue`, process the data, and place the results onto a `processed_news_queue` for the next service in the pipeline.
3.  **`main.py` as Orchestrator:** The main application entry point was overhauled to create and connect these queues, wiring all the services together. The startup and shutdown logic was also modernized and made more robust.

**Benefit:** This architecture is now fully non-blocking, truly decoupled, and provides a clear, scalable data pipeline for handling high-frequency events. 