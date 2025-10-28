### **Product Requirements Document: "Vision" Real-Time News Trading Bot**

### **1. Introduction & Vision**

**1.1. The Problem:** Financial markets react with extreme speed to breaking news. Capturing the initial momentum requires an automated system capable of identifying a relevant news event and executing a trade faster than a human can react.

**1.2. The Vision:** To create an automated trading system that visually monitors the Interactive Brokers (IBKR) news portal, uses an AI Vision model to identify the relevant stock ticker from new headlines, and executes a momentum-based trade based on the market's initial reaction.

**1.3. Core Workflow:**
1.  Visually detect new headlines in the IBKR Trader Workstation (TWS) news window.
2.  Capture an image of the new headline.
3.  Submit the image to a Large Language Model (LLM) to extract the stock ticker.
4.  Use the extracted ticker to analyze market data for a price/volume shock.
5.  Execute and manage a trade based on predefined rules.

### **2. Strategic Goals & Success Metrics**

**2.1. Goals:**
*   **Automation:** Fully automate the revised workflow from visual detection to trade execution.
*   **Accuracy:** Achieve the highest possible accuracy in ticker extraction from images to prevent trading the wrong asset.
*   **Resilience:** Build a system robust enough to handle potential UI and API disruptions.
*   **Profitability:** Achieve a net positive P&L over a statistically significant number of trades.

**2.2. Success Metrics:**
*   **Financial Metrics:**
    *   Net P&L (Profit & Loss)
    *   Win/Loss Ratio
    *   Sharpe Ratio (Risk-Adjusted Return)
*   **Performance Metrics:**
    *   **Ticker Extraction Accuracy:** Target > 99.5% accuracy on identifying the correct ticker from a screenshot.
    *   **End-to-End Latency:** Time from screen pixel change to IBKR order placement.
    *   **LLM API Success Rate:** Percentage of successful (non-error) API calls to the vision model.

### **3. System Features & User Stories**

**3.1. Module 1: Screen Monitoring & Capture Engine**
*   **Description:** A persistent desktop process that monitors a user-defined region of the screen for visual changes and captures images.
*   **User Story:** As a trader, I want the system to constantly watch the news feed window on my screen and automatically take a picture the instant a new headline appears.
*   **Requirements:**
    *   A configuration interface to define the screen coordinates (X, Y, width, height) of the "Region of Interest" (ROI) to monitor.
    *   An efficient pixel-change detection algorithm to trigger the capture process.
    *   A configurable sensitivity threshold to avoid false triggers from minor visual artifacts (e.g., a blinking cursor).
    *   The module must save the captured ROI as an image file (e.g., PNG) to a local directory.

**3.2. Module 2: OCR & Ticker Extraction (LLM Vision Service)**
*   **Description:** This module takes a captured image, sends it to an external LLM Vision API, and parses the response to extract a stock ticker.
*   **User Story:** As a trader, I want the system to send the captured news image to an AI service to read the text and accurately identify the stock ticker so the system knows which instrument to trade.
*   **Requirements:**
    *   Secure API integration with a specified LLM Vision service (e.g., GPT-4V, Google Gemini Vision).
    *   Management of API keys and credentials.
    *   A well-defined and tested prompt that instructs the LLM to perform OCR and return only the associated stock ticker in a structured format (e.g., JSON `{"ticker": "KITT"}`).
    *   Robust error handling for API call failures, timeouts, or responses that do not contain a valid ticker.
    *   A validation step to ensure the extracted ticker conforms to a valid market symbol format.

**3.3. Module 3: Event Detection & Qualification Engine**
*   **Description:** Receives a validated ticker from the LLM module and analyzes market data to confirm a tradeable "shock" event.
*   **User Story:** As a trader, after the system identifies a ticker, I want it to check the stock's live market data to confirm a significant price and volume surge is happening before placing a trade.
*   **Requirements:**
    *   Upon receiving a ticker, the system must immediately request market data from the IBKR API.
    *   A "Shock Detection Algorithm" must compare the current price/volume against a baseline to qualify a tradeable event.
    *   Must determine the direction of the trade (Long/Short) based on the price shock.
    *   Generate a trade signal (Ticker, Direction) if a shock is confirmed.

**3.4. Module 4: Trade Execution & Position Sizing**
*   **Description:** Receives a trade signal and is responsible for placing the order with IBKR.
*   **User Story:** As a trader, I want the system to execute trades as fast as possible with a calculated position size so that I can enter the market and manage my risk capital.
*   **Requirements:**
    *   **Order Type:** Must use **Market Orders** for speed of entry.
    *   **Position Sizing Algorithm:** Trade size (number of shares) will be determined by a predefined, configurable algorithm.
    *   Immediately transmit the order to IBKR upon receiving a valid signal.

**3.5. Module 5: Position & Risk Management**
*   **Description:** Monitors the open position and executes the exit based on predefined rules.
*   **User Story:** As a trader, I want the system to automatically exit my position based on my strategy so that I can lock in profits or cut losses without emotion.
*   **Requirements:**
    *   Continuously monitor the real-time P&L of the open position via the IBKR API.
    *   **Exit Logic:** Exit based on a configurable Take-Profit target, Stop-Loss threshold, or a maximum time-in-trade limit.

### **4. Assumptions, Risks, and Open Questions**

**4.1. Assumptions:**
*   The IBKR news window will remain in a fixed, unobstructed position on the screen during operation.
*   The chosen LLM Vision API will be consistently available, fast, and accurate.
*   The visual layout (font, color, structure) of the IBKR news feed will not change frequently.
*   The internet connection is stable and fast enough for rapid image uploads and API communication.

**4.2. CRITICAL RISKS:**
*   **Risk 1: Latency (HIGH):** The round-trip time for an LLM Vision API call (image upload, processing, response download) is the primary performance bottleneck and is expected to be in the multi-second range, which may be insufficient for the trading strategy.
*   **Risk 2: System Brittleness (HIGH):** The screen-scraping methodology is inherently fragile. Any change to the IBKR TWS user interface, or any OS-level interruption (pop-up notifications, other windows), will break the data ingestion pipeline.
*   **Risk 3: Accuracy & Hallucination (HIGH):** The entire trading decision rests on the LLM's ability to correctly perform OCR and extract the right ticker. An error (e.g., misreading "TSLA" as "TSL A", or confusing "O" with "0") will result in trading the wrong instrument, with potentially catastrophic financial consequences.
*   **Risk 4: API Cost & Rate Limits (MEDIUM):** High-frequency polling of a premium LLM Vision API may incur significant operational costs and could be subject to API rate limiting, causing the system to fail during periods of high news flow.

**4.3. Open Questions / Undefined Algorithms:**
*   Which specific LLM Vision provider and model will be used?
*   What is the exact prompt that will be engineered to maximize ticker extraction accuracy?
*   What is the programmatic error-handling logic if the LLM returns an invalid ticker, a hallucinated ticker, or no ticker at all?
*   What is the contingency plan for when the IBKR UI is updated, breaking the screen capture module?
*   How will the system be tested end-to-end without incurring significant LLM API costs during development?