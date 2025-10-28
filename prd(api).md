Of course. Understood. We will revert the architecture to the more robust and streamlined single-platform approach, using Interactive Brokers for all functions.

Here is the complete, updated Product Requirements Document for the project, reflecting the use of IBKR as the sole API for news, market data, and trade execution.

---

### **Product Requirements Document: "Momentum API" Real-Time News Trading Bot**

### **1. Introduction & Vision**

**1.1. The Problem:** Financial markets price in new information with extreme velocity. Manually trading on breaking news is impossible due to the speed required to ingest, analyze, and act. An automated solution is required to systematically capture the initial price movement driven by significant news events.

**1.2. The Vision:** To create a high-speed, automated trading system that connects directly to a low-latency news feed via the **Interactive Brokers (IBKR) API**. The system will programmatically identify news tied to a specific stock, analyze its market data for a reaction, execute a trade in the direction of the momentum, and manage the position based on a strict set of rules, all within the IBKR ecosystem.

**1.3. Core Workflow:**
1.  Establish a persistent, resilient connection to the **IBKR API**.
2.  Subscribe to a real-time, machine-readable news feed (e.g., Benzinga) through the **IBKR API**.
3.  Instantly parse incoming structured news data to extract the stock ticker.
4.  Upon receiving a ticker, analyze live market data, also from the **IBKR API**, for a qualifying price/volume "shock."
5.  Execute a market order to enter a position and apply a predefined risk management strategy to exit, all via the **IBKR API**.

### **2. Strategic Goals & Success Metrics**

**2.1. Goals:**
*   **Automation:** Fully automate the entire trading lifecycle from news event to position close.
*   **Speed:** Minimize end-to-end latency from the moment a news item is published to the moment an order is confirmed by the exchange.
*   **Reliability:** Build a robust system with a stable connection and consistent data processing, capable of handling the daily IBKR restart.
*   **Profitability:** Achieve a net positive P&L under the specified trading strategy.

**2.2. Success Metrics:**
*   **Financial Metrics:**
    *   Net P&L (Profit & Loss)
    *   Win/Loss Ratio
    *   Average Profit per Winning Trade vs. Average Loss per Losing Trade
    *   Sharpe Ratio (Risk-Adjusted Return)
*   **Performance Metrics:**
    *   **End-to-End Latency:** Time from the news article's API timestamp to IBKR order confirmation (Target: < 200ms).
    *   **API Message Processing Time:** Time taken by the application to parse a news object and generate a trade signal (Target: < 10ms).
    *   **Slippage:** Average monetary difference between the market price at signal generation and the final execution price.
    *   **System Uptime:** Must be > 99.9% during trading days (including pre-market, post-market, and overnight sessions).

### **3. System Features & User Stories**

**3.1. Module 1: IBKR Gateway Connection**
*   **Description:** The foundational, state-aware module responsible for connecting to the IBKR Gateway and managing the entire API session.
*   **User Story:** As a trader, I need the system to securely and reliably connect to my IBKR account so that it can access all required services (news, data, trading) and automatically recover from the daily mandatory logoff.
*   **Requirements:**
    *   Securely manage and utilize IBKR API credentials.
    *   Implement a robust state machine (`DISCONNECTED`, `CONNECTING`, `OPERATIONAL`) to manage connection status.
    *   Implement automatic reconnection logic with exponential backoff to handle the daily restart and other network drops.
    *   Upon reconnection, perform a state synchronization checklist (re-subscribe to feeds, reconcile open positions and orders) before becoming operational.

**3.2. Module 2: Real-Time News Ingestion & Parsing**
*   **Description:** This module subscribes to the specified news feed via the IBKR API and processes the incoming structured data.
*   **User Story:** As a trader, I want the system to listen to a high-speed Benzinga news feed via the API and instantly read the ticker symbol from each news item as it arrives.
*   **Requirements:**
    *   Correctly subscribe to the designated premium news provider (e.g., Benzinga).
    *   The parser must be built to handle the IBKR news API object structure (e.g., XML), correctly identifying fields for timestamp and associated tickers.
    *   Efficiently filter out news items that do not contain a stock ticker.
    *   The module must be non-blocking (following a producer-consumer pattern) and capable of handling a high-velocity stream of news.

**3.3. Module 3: Event Detection & Qualification Engine**
*   **Description:** The core logic engine that receives a ticker and determines if a tradeable event is occurring using IBKR market data.
*   **User Story:** As a trader, once the system gets a ticker from a news alert, I want it to immediately check the stock’s live price and volume from IBKR to confirm a significant surge is happening before it decides to trade.
*   **Requirements:**
    *   Upon receiving a valid ticker, the system must issue a high-priority request for real-time market data (candles and quotes) from **IBKR**.
    *   The configurable "Shock Detection Algorithm" will qualify a tradeable event based on thresholds for price and volume, using the **IBKR data feed**.
    *   Generate an immutable trade signal for the execution module.

**3.4. Module 4: Trade Execution & Position Sizing**
*   **Description:** This module is responsible for placing orders based on signals from the qualification engine.
*   **User Story:** As a trader, I want the system to instantly place an order with a calculated share size as soon as the qualification engine confirms a valid trade signal.
*   **Requirements:**
    *   **Order Type:** Must use **Market Orders** to ensure the fastest possible entry.
    *   **Position Sizing Algorithm:** Trade size must be calculated based on a configurable model.
    *   The module must confirm the order was accepted by IBKR and log the execution details.
    *   **Gating Logic:** Must check if the IBKR connection is fully `OPERATIONAL` before attempting to send any order.

**3.5. Module 5: Position & Risk Management**
*   **Description:** Once a position is open, this module actively manages it until exit using IBKR data.
*   **User Story:** As a trader, I want the system to watch my open position second-by-second and automatically sell it to lock in my target profit or cut my losses according to my plan.
*   **Requirements:**
    *   Subscribe to real-time market data from **IBKR** for the open position to track P&L.
    *   Implement exit rules using a predefined Take-Profit target, a hard Stop-Loss, and a "max time in trade" fail-safe.

### **4. Assumptions, Risks, and Algorithms**

**4.1. Assumptions:**
*   A subscription to a premium, low-latency news provider (like Benzinga Pro for API) via IBKR is active.
*   The IBKR market data feed is of sufficient quality and speed for the strategy's requirements.
*   The IBKR API and the user's network infrastructure are fast enough to execute the strategy.

**4.2. CRITICAL RISKS:**
*   **Risk 1: Latency Disadvantage (HIGH):** While using a single API is efficient, the strategy still competes with institutional firms co-located with exchange data centers. The inherent latency of a retail internet connection could result in suboptimal entry prices.
*   **Risk 2: Execution Risk (HIGH):** The strategy specifically targets high-volatility moments. This exposes all market orders to significant **slippage** and **wide bid-ask spreads**, which can severely impact profitability.
*   **Risk 3: Single Point of Failure (MEDIUM):** The entire operation is dependent on the uptime and performance of the Interactive Brokers API. Any outage or issue with their service will halt all trading activity.

**4.3. Algorithms:**

**4.3.1. Shock Detection Algorithm:**
This algorithm is designed to qualify a tradeable event by confirming that a news-driven price move is statistically significant compared to the stock's recent behavior. A shock is confirmed if **both** of the following conditions are met for the most recent 1-minute candle, using data from IBKR.

*   **Condition 1: Price Shock.** `(|Close - Open| / Open) > (ATR(10) / Open) * Price_Multiplier`
*   **Condition 2: Volume Shock.** `Current_Volume > SMA(Volume, 20) * Volume_Multiplier`
*   **Configurable Parameters:**
    *   `ATR(10)`: The 10-period Average True Range.
    *   `Price_Multiplier`: (Default: **3.0**).
    *   `SMA(Volume, 20)`: The 20-period Simple Moving Average of volume.
    *   `Volume_Multiplier`: (Default: **5.0**).

**4.3.2. Position Sizing Algorithm:**
This algorithm calculates the number of shares to trade using the Fixed Fractional (or Percentage Risk) risk management model to ensure consistent risk exposure.

*   **Formula:** `Position_Size_in_Shares = floor((Account_Value * Risk_Per_Trade_%) / (|Entry_Price - Stop_Loss_Price|))`
*   **Configurable Parameters & Inputs:**
    *   `Account_Value`: The total current equity of the trading account, fetched from IBKR.
    *   `Risk_Per_Trade_%`: The maximum percentage of account value to risk. (Default: **1.0%** or `0.01`).
    *   `Entry_Price`: The actual fill price of the market order.
    *   `Stop_Loss_Price`: The calculated price at which the stop-loss will be placed.