import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import trend

if __name__ == "__main__":
    # 時刻を定義
    utc = datetime.now(tz=timezone.utc)
    utc_yesterday = utc - timedelta(days=1)

    # Googleトレンドからデータを取得する
    google = trend.google().drop("formattedTraffic", 1).rename(columns={"title": "key", "traffic": "count"})
    google["source"] = "trends.google.com"

    # Twitterのトレンドからデータを取得する
    twitter = trend.twitter().rename(columns={"name": "key", "tweet_volume": "count"})
    twitter["source"] = "twitter.com"

    # データを組み合わせる
    latest = pd.concat([google, twitter]).reset_index(drop=True)
    latest["date"] = utc.isoformat()

    # データベースから過去データを読み込む
    db_path = Path("cache/word_database.csv")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if db_path.is_file():
        db = pd.read_csv(db_path)
    else:
        db = pd.DataFrame()

    # データを追加する
    db = pd.concat([db, latest]).reset_index(drop=True)

    # 古いデータを削除
    db = db[pd.to_datetime(db.date, utc=True) > utc_yesterday]

    # データベースに書き込む
    db.to_csv(db_path, index=False)

    # ランキングの作成
    rank = pd.DataFrame(db.rename(columns={"key": "title"}), columns=["title", "score", "updated_at", "chart"]).drop_duplicates(subset=["title"]).reset_index(drop=True)
    rank.updated_at = rank.title.apply(lambda x: db[db.key == x]["date"].iloc[-1])

    # スコアの算出
    def calc_score(title):
        traffic = db[db.key == title]["count"].reset_index(drop=True)
        diff = traffic.diff().dropna().reset_index(drop=True)

        score = traffic.median() / 2 + np.nan_to_num(diff.median())

        print(title, score)

        return score

    rank.score = rank.title.apply(calc_score)

    # チャートの作成
    def create_chart(title):
        df = db[db.key == title].reset_index(drop=True)
        df["hour"] = df.date.apply(lambda x: (pd.to_datetime(x, utc=True).to_pydatetime() - utc).total_seconds() // 3600)
        df = df.drop_duplicates(subset=["hour", "source"]).reset_index(drop=True)

        print(df)

        df = df.pivot(index="hour", columns="source", values="count").reindex(pd.RangeIndex(start=-23, stop=1))

        print(df)

        c = {
            "type": "line",
            "data": {
                "labels": df.index.tolist(),
                "datasets": [
                    {
                        "label": key,
                        "data": value.fillna(0).tolist(),
                        "fill": "false",
                    }
                    for key, value in df.iteritems()
                ],
            },
            "options": {
                "title": {
                    "display": "true",
                    "text": title,
                },
            },
        }

        return "https://quickchart.io/chart?bkg=white&c=" + urllib.parse.quote(str(c))

    rank.chart = rank.title.apply(create_chart)

    # スコア順にソート
    rank = rank.sort_values(by=["score"], ascending=False).reset_index(drop=True)

    print(rank)

    # ランキングをファイルに書き込む
    rank_path = Path("public/word.json")
    rank_path.parent.mkdir(parents=True, exist_ok=True)

    rank.to_json(rank_path, orient="records")
