import requests
import json
from datetime import datetime, timedelta
import time
import pandas as pd
import time
from datetime import datetime, timedelta

class BenzingaPressReleases:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.benzinga.com/api/v2"
        self.headers = {
            "accept": "application/json"
        }
        
    def get_press_releases(self, tickers=None, updated_since=None, 
                          page_size=100, channels="Press Releases"):
        """
        Fetch press releases from Benzinga
        
        Args:
            tickers: List of stock symbols (max 50)
            updated_since: Unix timestamp for delta updates
            page_size: Number of results (max 100)
            channels: Filter by channel (default "Press Releases")
        """
        endpoint = f"{self.base_url}/news"
        
        params = {
            "token": self.api_key,
            "pageSize": page_size,
            "displayOutput": "full"  # Get full content
        }
        
        # Add optional filters
        if channels:
            params["channels"] = channels
            
        if tickers:
            if isinstance(tickers, list):
                params["tickers"] = ",".join(tickers[:50])  # Max 50
            else:
                params["tickers"] = tickers
                
        if updated_since:
            # Benzinga recommends 5-second lag for reliability
            lagged_timestamp = updated_since - 5
            params["updated"] = lagged_timestamp
            
        response = requests.get(endpoint, params=params, headers=self.headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return None





# Initialize
API_KEY = "bz.QFOSGT5DU2GTXOCRBRJC3QRR532WDP3G"

# Monitor specific companies
companies = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]

# Callback function for press releases
def handle_press_release(pr_data):
    # Send alert
    print(f"ALERT: New press release for {pr_data['ticker']}")
    
    # Save to database
    # db.save_press_release(pr_data)
    
    # Execute trading logic
    # if 'earnings' in pr_data['title'].lower():
    #     execute_earnings_strategy(pr_data)


# Example 2: Get press releases from the last week
week_ago_timestamp = int((datetime.now() - timedelta(days=7)).timestamp())

benzingaPressReleases = BenzingaPressReleases(API_KEY)
result = benzingaPressReleases.get_press_releases(tickers="INTC", updated_since=week_ago_timestamp)
print(json.dumps(result, indent = 2))