import finnhub
finnhub_client = finnhub.Client(api_key="d30e8phr01qnmrse5pm0d30e8phr01qnmrse5pmg")

print(finnhub_client.stock_symbols('US'))