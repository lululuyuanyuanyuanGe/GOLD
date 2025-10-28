### **Prompt for AI Coding Agent: Implementation of the 'Momentum API' Trading Bot**

**Role:** You are an expert Python software engineer specializing in building high-performance, asynchronous financial applications. Your code should be clean, robust, modular, and production-ready.

**Primary Objective:** Your task is to implement the complete, end-to-end source code for the "Momentum API" algorithmic trading bot. You will be provided with two critical documents that you **MUST** use as the single source of truth for this implementation: the **Product Requirements Document (PRD)** and the **Technical Design & Architecture Document (TSD)**.

Think of the PRD as the **"what"** (what the system does) and the TSD as the **"how"** (how the system is built). Your implementation must perfectly reflect both.

---

### **Core Instructions:**

1.  **Strict Adherence to Documents:** You must strictly adhere to the architecture, modules, technology stack, data flow, and logic defined in the TSD and PRD. Do not introduce new libraries, change the core architectural patterns (e.g., the producer-consumer model), or deviate from the specified algorithms.
2.  **Asynchronous Implementation:** The entire application must be built on Python's `asyncio` library. All I/O-bound operations (API calls, waiting for events) must use `async/await` syntax to be non-blocking.
3.  **Project Structure:** Generate the complete source code for the project, presenting it in a file-by-file format that exactly matches the directory structure specified in the TSD.
4.  **Code Quality & Best Practices:**
    *   **PEP 8:** All code must be formatted according to PEP 8 standards.
    *   **Type Hinting:** Use modern Python type hints for all function signatures, variables, and class members.
    *   **Modularity:** Encapsulate all logic within the specific modules defined in the TSD (`IBKRConnector`, `NewsHandler`, `DetectionEngine`, etc.). Do not mix responsibilities.
    *   **Configuration:** All parameters (API settings, strategy variables, file paths) must be loaded from a central `config.yaml` file. **Do not hardcode any values in the Python source code.**
    *   **Logging:** Implement structured logging throughout the application. Log important events such as connections, disconnections, news received, signals generated, orders placed, and errors.
    *   **Error Handling:** Include robust `try...except` blocks for all network operations and external API calls.
5.  **Placeholders:** Use placeholder values for sensitive information in the `config.yaml` file (e.g., `YOUR_ACCOUNT_ID`, `YOUR_HOST`, `YOUR_PORT`).
6.  **Completeness:** Generate the content for **all** necessary project files, including:
    *   All Python source files (`.py`).
    *   The `config.yaml` template.
    *   The `pyproject.toml` file, specifying all dependencies mentioned in the TSD (`ib_insync`, `pandas`, `numpy`, `pyyaml`, `poetry`).
    *   A basic `.gitignore` file suitable for a Python project.
    *   A `README.md` that briefly describes the project and how to run it.
7.  **Focus on Implementation:** Do not provide explanations of the code in your response unless they are comments within the code itself. The goal is the final, ready-to-use codebase.