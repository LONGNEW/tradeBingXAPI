import json
import pandas as pd
import numpy as np
import temp_bingx
import temp_macd_bingX
import Gmail
from firebase_admin import db
from datetime import datetime, timedelta

APIURL = "https://open-api.bingx.com"
APIKEY = db.reference("/bingx_APIKEY").get()
SECRETKEY = db.reference("/bingx_SECRETKEY").get()

# bingx에서 가져오는 가격들은 시간이 순서대로임
# 0부터 현재시간 idx 커질수록 예쩐

# binance에서는 0부터 과거시간, idx 커질수록 현재
def only_1_prices(symbol, interval="4h"):
    payload = {}
    path = '/openApi/swap/v3/quote/klines'
    method = "GET"

    now = datetime.now()
    one_day_ago = now - timedelta(days=1)
    milliseconds = int((one_day_ago - datetime(1970, 1, 1)).total_seconds() * 1000)

    paramsMap = {
    "symbol": symbol,
    "interval": interval,
    "limit": "1000",
    "startTime": str(milliseconds)
}
    paramsStr = temp_bingx.praseParam(paramsMap)
    res = json.loads(temp_bingx.send_request(method, path, paramsStr, payload))

    return res["data"]

def buy_or_sell(symbol, balance, interval):
    # 이전 캔들 몸통의 절반이 볼린저 밴드를 벗어난 경우.
    Up, mid, Low = check_bollinger(symbol, interval)
    print(f"{symbol} BB, mid: {mid}, up: {Up}, low: {Low}")

    # 포지션 없는지 체킹
    # 없으면 포지션 open
    coin, currency = symbol.split("-")
    flag, side = temp_bingx.check_positions(symbol)
    BB_pos = db.reference(f"BB/{coin}_pos").get()

    if mid >= Up:
        # Buy Signal
        print(f"{symbol}에서 BB 상향돌파 발생!")
        print(f"총 {balance}$만큼의 주문 시작!\n")
        # temp_bingx.order(symbol, 1, balance)

        db.reference().update({f"BB/{coin}_pos": 1})
        Gmail.send_email(f"Bingx : {symbol} 포지션 오픈 완료! BB 상향돌파 발생")
        print("주문 완료!\n")

        return 1

    if mid <= Low:
        print(f"{symbol}에서 BB 하향돌파 발생!")
        print(f"총 {balance}$만큼의 주문 시작!\n")
        # temp_bingx.order(symbol, -1, balance)

        db.reference().update({f"BB/{coin}_pos": 1})
        Gmail.send_email(f"Bingx : {symbol} 포지션 오픈 완료! BB 하향돌파 발생")
        print("주문 완료!\n")
        return 1

    # 포지션 있는지 체킹
    # 있으면 포지션 close
    # If nothing match, just close the position
    if BB_pos and flag:
        print(f"{symbol}에서 돌파 상황 종료")
        temp_bingx.wipe_order(symbol)
        db.reference().update({f"BB/{coin}_pos": 0})
        print("포지션 처분 완료\n")
        return 0

    print("조건 불만족...\n")
    return 0


def check_bollinger(symbol, interval, length = 20, ratio = 2, before=-2):
    prices = temp_macd_bingX.get_prices(symbol, interval, "close")

    df = pd.DataFrame({'Close': prices})
    df['MA'] = np.round(df['Close'].rolling(window=20).mean(), decimals=1)

    # 분산, 표준편차 구하기
    window_size = length
    rolling_means = []
    rolling_stds = []

    for i in range(len(prices) - window_size + 1):
        window_data = prices[i:i + window_size]
        mean_value = sum(window_data) / window_size
        std_value = (sum((x - mean_value) ** 2 for x in window_data) / window_size) ** 0.5
        rolling_means.append(mean_value)
        rolling_stds.append(std_value)

    # 볼린져 밴드의 위 아래 값
    Upperband = [mean + (ratio * std) for mean, std in zip(rolling_means, rolling_stds)]
    LowerBand = [mean - (ratio * std) for mean, std in zip(rolling_means, rolling_stds)]

    # 4시간 이전 캔들 가격 가지고 옴.
    price_data = only_1_prices(symbol)[1]
    middle_price = (float(price_data["open"]) + float(price_data["close"])) / 2

    # if middle_price
    return Upperband[before], middle_price, LowerBand[before]

if __name__ == '__main__':
    for symbol in ["BTC-USDT", "ETH-USDT", "SOL-USDT",
                   "ORDI-USDT", "MASK-USDT",
                   "NEAR-USDT", "ICP-USDT"]:
        Up_20, _, Low_20 = check_bollinger(symbol, "1h")
        Up_4, _, Low_4 = check_bollinger(symbol, "1h", 4, 4)
        price_data = only_1_prices(symbol, "1h")[1]
        high, low = float(price_data["high"]), float(price_data["low"])

        decimal_places1 = len(str(high).split('.')[-1])
        decimal_places2 = len(str(low).split('.')[-1])

        # 두 숫자 중 더 많은 소수점 위치로 반올림
        decimal_cnt = max(decimal_places1, decimal_places2) - 1
        high, low = round(high, decimal_cnt), round(low, decimal_cnt)
        Up_20, Low_20 = round(Up_20, decimal_cnt), round(Low_20, decimal_cnt)
        Up_4, Low_4 = round(Up_4, decimal_cnt), round(Low_4, decimal_cnt)

        print(f"{symbol}의 double BB")
        print(f"상한 비교 { Up_4 <= high}: {Up_20}, {Up_4}, {high}")
        print(f"하한 비교 {low <= Low_4}: {Low_20}, {Low_4}, {low}")
        flag = False
        if not flag and Up_20 <= high and Up_4 <= high:
            flag = True
        if not flag and low <= Low_20 and low <= Low_4:
            flag = True
        if flag:
            print(f"조건 만족하여 이메일 전송!!!\n")
            Gmail.send_email(f"BingX: {symbol}에서 Double BB의 상한 혹은 하한을 찌르는 상황 발생!")
        else:
            print(f"조건 불만족...\n")
