import aiohttp
import asyncio
import json
import logging
import os
from typing import Optional

# In a real application, these should come from a secure config or environment loader
DEFAULT_AI_API_URL = os.environ.get("AI_API_URL", "https://api.openai.com/v1/chat/completions")
DEFAULT_AI_MODEL = os.environ.get("AI_MODEL", "gpt-3.5-turbo")
API_KEY = os.environ.get("AI_API_KEY")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def extract_symbols_with_ai(
    news_text: str,
    session: aiohttp.ClientSession,
    api_url: str = DEFAULT_AI_API_URL,
    model: str = DEFAULT_AI_MODEL,
    api_key: Optional[str] = API_KEY
) -> list[str]:
    """
    Uses an external AI API to parse news text and extract stock symbols.

    Args:
        news_text: The raw text of the news article.
        session: An aiohttp.ClientSession object for making requests.
        api_url: The URL of the AI API endpoint.
        model: The name of the AI model to use.
        api_key: The API key for authentication.

    Returns:
        A list of extracted stock symbols, or an empty list if none are found or an error occurs.
    """
    if not api_key:
        logging.error("AI_API_KEY environment variable not set. Cannot extract symbols with AI.")
        return []

    prompt = f"""
    From the following news article text, extract all relevant US stock market ticker symbols.
    The article may contain noise, XML tags, or other non-relevant information.
    Focus only on the ticker symbols (e.g., AAPL, GOOG, MSFT).
    Return the symbols as a JSON-formatted list of strings. For example: ["TICK1", "TICK2"].
    If no symbols are found, return an empty list [].

    Article Text:
    ---
    {news_text}
    ---
    """

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"}  # Use JSON mode for reliable output
    }

    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with session.post(api_url, headers=headers, json=payload, timeout=timeout) as response:
            response.raise_for_status()
            response_json = await response.json()
            
            content = response_json.get("choices", [{}])[0].get("message", {}).get("content", "[]")
            
            symbols = json.loads(content)
            
            if isinstance(symbols, list):
                # Basic validation for ticker-like strings
                return [str(s).upper() for s in symbols if isinstance(s, str) and 1 <= len(s) <= 5 and s.isalpha()]
            else:
                logging.warning(f"AI response was not a list: {symbols}")
                return []

    except aiohttp.ClientError as e:
        logging.error(f"AI API request failed: {e}")
        return []
    except json.JSONDecodeError as e:
        logging.error(f"Failed to decode JSON from AI response: {e} - Response content: {content}")
        return []
    except Exception as e:
        logging.error(f"An unexpected error occurred during AI symbol extraction: {e}", exc_info=True)
        return []
