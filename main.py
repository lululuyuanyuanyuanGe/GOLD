import requests

api_key = 'bz.QFOSGT5DU2GTXOCRBRJC3QRR532WDP3G'
url = 'https://api.benzinga.com/api/v2/news'

params = {
    'token': api_key,
    'tickers': 'AAPL',
    'channels': 'Press Releases',
    'displayOutput': 'full',
    'pageSize': 10
}

# Just use params, don't encode manually
response = requests.get(url, params=params)

if response.status_code == 200:
    data = response.json()
    for article in data:
        print(f"Title: {article.get('title', 'N/A')}")
        print(f"Date: {article.get('created', 'N/A')}")
        if 'body' in article:
            print(f"Content: {article['body'][:200]}...")
        print("-" * 50)
else:
    print(f"Error: {response.status_code}")
    print(f"Response: {response.text[:500]}")