# Full programmatic access to press releases
# $178/month total

from polygon import RESTClient

client = RESTClient("")

# Get Benzinga press releases via Polygon
news = client.reference_news_v2(
    ticker="AAPL",
    published_utc_gte="2024-01-01"
)

for article in news:
    if "press release" in article.keywords:
        # Process press release
        print(f"PR: {article.title}")