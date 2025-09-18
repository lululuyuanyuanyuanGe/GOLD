import requests
import json
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()

# Your FMP API key (get this from your account dashboard)
API_KEY = os.getenv("FMP_API_KEY")
BASE_URL = "https://financialmodelingprep.com"

def make_request(endpoint, params: dict{} = None):
    """Helper function to make API requests with error handling"""
    if params is None:
        params = {}
    
    params['apikey'] = API_KEY
    
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return None


def get_latest_press_releases(limit:int =50):
    """Fetch the latest press releases from all companies"""
    endpoint = "/stable/news/press-releases-latest"
    params = {'limit': limit}
    
    data = make_request(endpoint, params=params)
    
    if data:
        print(f"Retrieved {len(data)} press releases")
        for release in data[:5]:  # Show first 5
            print(f"- {release['title']}")
            print(f"  Company: {release['symbol']}")
            print(f"  Date: {release['date']}")
            print(f"  URL: {release['url']}")
            print()
    
    return data

# Usage
latest_releases = get_latest_press_releases()
print(latest_releases)
