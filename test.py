import requests
import os
from dotenv import load_dotenv
import json

load_dotenv()

API_KEY = os.getenv("NEWS_API_KEY")
params = {
    "apiKey": API_KEY,
    "language": "en",
    "country": "us"
}

response = requests.get("https://newsapi.org/v2/top-headlines/sources", params=params)
response = response.json()
print(json.dumps(response, indent=2))

