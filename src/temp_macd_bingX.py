import json
import pandas as pd
import numpy
import temp_bingx
from datetime import datetime, timedelta
from firebase_admin import db

APIURL = "https://open-api.bingx.com"
APIKEY = db.reference("/bingx_APIKEY").get()
SECRETKEY = db.reference("/bingx_SECRETKEY").get()

def get_prices(symbol, interval, which):
    payload = {}
    path = '/openApi/swap/v3/quote/klines'
    method = "GET"

    now = datetime.now()
    ten_days_ago = now - timedelta(days=20)
    milliseconds = int((ten_days_ago - datetime(1970, 1, 1)).total_seconds() * 1000)

    paramsMap = {
    "symbol": symbol,
    "interval": interval,
    "limit": "1000",
    "startTime": str(milliseconds)
}
    paramsStr = temp_bingx.praseParam(paramsMap)
    res = json.loads(temp_bingx.send_request(method, path, paramsStr, payload))

    data = []
    for item in res["data"][::-1]:
        data.append(float(item[which]))
    return data


def check_macd(symbol):
    # 여기서 interval 지정
    prices = get_prices(symbol, "30m", "open")
    df = pd.DataFrame({'open': prices})
    df2 = df['open'].to_numpy()

    now_price = temp_bingx.real_time_price(symbol)
    df2 = numpy.append(df2, [now_price])

    df = pd.DataFrame(df2, columns=['open'])

    exp1 = df['open'].ewm(span=12, adjust=False).mean()
    exp2 = df['open'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    macd = macd.values

    macd2, macd1 = macd[-3], macd[-2]
    print(f"1시간 전 : {macd[-3]}, 30분 전 : {macd[-2]}")
    if macd2 < 0 and 0 <= macd1:
        return 1

    if macd2 >= 0 and 0 > macd1:
        return -1

    return 0

if __name__ == '__main__':
    print("demo:", check_macd("BTC-USDT"))
