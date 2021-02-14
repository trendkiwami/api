import pandas as pd
import tweepy
from pytrends.request import TrendReq


def parse_traffic(text):
    # TODO: str.removesuffix in Python 3.9
    if text.endswith("+"):
        text = text[: -len("+")]

    unit = ["K", "M", "B", "T"]

    if text.endswith(tuple(unit)):
        at = unit.index(text[-1]) + 1
        text, multiple = text[:-1], 10 ** (3 * at)
    else:
        multiple = 1

    return int(text) * multiple


def google():
    api = TrendReq()

    trend_data = api._get_data(TrendReq.TODAY_SEARCHES_URL, trim_chars=5, params={"geo": "JP"})["default"]["trendingSearchesDays"][0]["trendingSearches"]
    trend = pd.DataFrame(trend_data, columns=["title", "formattedTraffic"])
    trend.title = trend.title.apply(lambda x: x["query"])
    trend["traffic"] = trend.formattedTraffic.apply(parse_traffic)

    print(trend)

    return trend


def twitter(consumer_key="3nVuSoBZnx6U4vzUxf5w", consumer_secret="Bcs59EFbbsdF6Sl9Ng71smgStWEGwXXKSjYvPVt7qys", dropna=True):
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    api = tweepy.API(auth)

    region_data = api.trends_available()
    region = pd.DataFrame(region_data)

    japan = region[region.name == "Japan"].reset_index(drop=True)

    print(japan)

    trend_data = api.trends_place(japan.woeid.item())[0]["trends"]
    trend = pd.DataFrame(trend_data, columns=["name", "tweet_volume"])

    if dropna:
        trend = trend.dropna(subset=["tweet_volume"]).reset_index(drop=True)

    print(trend)

    return trend
