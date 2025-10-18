# Project Overview

This project is a Python-based financial data and trading platform that leverages the Interactive Brokers (IBKR) API. It is designed to be a comprehensive tool for traders and analysts, providing real-time and historical news, market data, and the foundation for automated trading strategies.

The application connects to the IBKR Trader Workstation (TWS) or Gateway to access a wide range of financial data and services. The core of the project is the `IBKR/main.py` script, which establishes the connection and manages the data streams.

## Key Features

*   **Real-time News:** Subscribes to real-time news feeds for specified stock symbols.
*   **Historical News:** Fetches historical news articles for in-depth analysis.
*   **Contract Details:** Retrieves contract information for various financial instruments.
*   **Extensible Architecture:** The `IBApp` class is designed to be extended with more functionality, such as order placement, account management, and real-time market data.
*   **Multi-source Data:** While the primary focus is on IBKR, the project also includes modules for fetching data from other sources like Benzinga.

## Key Technologies

*   **Python:** The core language for the project.
*   **ibapi:** The official Python API for Interactive Brokers.
*   **requests:** Used for making HTTP requests to other data providers.
*   **pandas:** Included as a dependency, suggesting future plans for data analysis and manipulation.

## Architecture

The project is centered around the `IBApp` class in `IBKR/main.py`, which inherits from the `EWrapper` and `EClient` classes of the `ibapi` library. This class handles the communication with the IBKR TWS/Gateway and processes the incoming data.

*   `IBKR/main.py`: The main application logic, including the `IBApp` class and the main execution loop.
*   `main.py`: A supplementary script for fetching news from the Benzinga API.
*   `test.py`: An exploratory script that demonstrates a more structured way to fetch data from Benzinga.
*   `pyproject.toml`: Defines the project dependencies and metadata.

# Building and Running

There are no explicit build steps. To run the project, you need to have Python and the dependencies installed.

**1. Install Dependencies:**

```bash
pip install -r requirements.txt 
# or, if you are using uv 
uv pip install -r requirements.txt
```
*(Note: a `requirements.txt` file can be generated from `pyproject.toml`)*


**2. Run the Interactive Brokers script:**

Before running the IBKR script, you must have the Interactive Brokers Trader Workstation (TWS) or Gateway running and configured to accept API connections.

```bash
python IBKR/main.py
```

**3. Run the supplementary scripts:**

```bash
python main.py
python test.py
```

# Development Conventions

*   **Modular Design:** The project is structured with a clear separation of concerns, with the core IBKR logic isolated in its own module.
*   **Asynchronous Operations:** The use of threading in `IBKR/main.py` allows for non-blocking communication with the IBKR API, which is essential for real-time data processing.
*   **Modern Python:** The use of `pyproject.toml` for dependency management aligns with modern Python packaging standards.
*   **API Abstraction:** The `BenzingaPressReleases` class in `test.py` demonstrates a good practice of abstracting API interactions into reusable classes.

# Future Development

The project has a solid foundation that can be extended in many ways:

*   **Order Management:** Implement functionality to place, modify, and cancel orders through the IBKR API.
*   **Real-time Market Data:** Subscribe to real-time market data streams for stocks, options, and other instruments.
*   **Trading Strategy Implementation:** Build and integrate automated trading strategies that react to news and market data.
*   **Database Integration:** Store the collected data in a database for more robust analysis and backtesting.
*   **GUI or Web Interface:** Create a user interface to visualize the data and manage the trading strategies.
