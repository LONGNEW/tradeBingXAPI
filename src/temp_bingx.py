import time
import requests
import hmac
import json
from hashlib import sha256
from datetime import datetime, timedelta

import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

cred = credentials.Certificate('mykey.json')
# cred = credentials.Certificate('mykey.json')
firebase_admin.initialize_app(cred,{
    'databaseURL' : ''
})

APIURL = "https://open-api.bingx.com"
APIKEY = db.reference("/bingx_APIKEY").get()
SECRETKEY = db.reference("/bingx_SECRETKEY").get()

def switch_levarage(symbol, leverage):
    payload = {}
    path = '/openApi/swap/v2/trade/leverage'
    method = "POST"

    current_time = datetime.now()
    milliseconds = int(current_time.timestamp() * 1000)

    paramsMap = {
        "leverage": leverage,
        "side": "SHORT",
        "symbol": symbol,
        "timestamp": str(milliseconds)
    }
    paramsStr = praseParam(paramsMap)
    res = json.loads(send_request(method, path, paramsStr, payload))

    return res

def check_positions(symbol):
    payload = {}
    path = '/openApi/swap/v2/trade/allOrders'
    method = "GET"

    now = datetime.now()
    now_milliseconds = int(now.timestamp() * 1000)
    ten_days_ago = now - timedelta(days=7)
    past_milliseconds = int((ten_days_ago - datetime(1970, 1, 1)).total_seconds() * 1000)

    paramsMap = {
        "endTime": str(now_milliseconds),
        "limit": "500",
        "startTime": str(past_milliseconds),
        "symbol": symbol,
        "timestamp": str(now_milliseconds)
    }
    paramsStr = praseParam(paramsMap)
    res = json.loads(send_request(method, path, paramsStr, payload))
    orders = res["data"]["orders"]
    last_order = orders[-1]

    # if profit is 0.0000 => opening
    # profit is not => closed
    if last_order["profit"] == "0.0000":
        return True, last_order["side"]
    return False, last_order["side"]

def wipe_order(symbol):
    payload = {}
    path = '/openApi/swap/v2/trade/closeAllPositions'
    method = "POST"

    current_time = datetime.now()
    milliseconds = int(current_time.timestamp() * 1000)

    paramsMap = {
        "timestamp": milliseconds,
        "symbol": symbol,
        "recvWindow": "10000"
    }
    paramsStr = praseParam(paramsMap)
    res = send_request(method, path, paramsStr, payload)
    return res

def set_SL(symbol, position, quantity, symbol_price, loss_percen):
    lo_diff = ((symbol_price / 100) * loss_percen)
    payload = {}
    path = '/openApi/swap/v2/trade/order'
    method = "POST"

    # stop loss 걸기
    paramsMap = {
        "symbol": symbol,
        "side": "BUY" if position != 1 else "SELL",
        "positionSide": "BOTH",
        "type": "STOP_MARKET",
        "quantity": quantity,
        "stopPrice": symbol_price + lo_diff if position != 1 else symbol_price - lo_diff,
        "reduceOnly": "true"
    }
    paramsStr = praseParam(paramsMap)
    res = json.loads(send_request(method, path, paramsStr, payload))
    error = res["code"]
    print(f"SL open : {error}")
    return

def set_TP(symbol, position, quantity, symbol_price, earn_percen):
    hi_diff = ((symbol_price / 100) * earn_percen)
    payload = {}
    path = '/openApi/swap/v2/trade/order'
    method = "POST"

    # take profit 걸기
    paramsMap = {
        "symbol": symbol,
        "side": "BUY" if position != 1 else "SELL",
        "positionSide": "BOTH",
        "type": "TAKE_PROFIT_MARKET",
        "quantity": quantity,
        "stopPrice": symbol_price - hi_diff if position != 1 else symbol_price + hi_diff,
        "reduceOnly": "true"
    }
    paramsStr = praseParam(paramsMap)
    res = json.loads(send_request(method, path, paramsStr, payload))
    error = res["code"]
    print(f"TP open : {error}")
    return

# bingx에서는 "-" 포함해서 symbol 이름을 작성
def order(symbol, position, balance):
    payload = {}
    path = '/openApi/swap/v2/trade/order'
    method = "POST"

    flag, side = check_positions(symbol)
    if (side == "SELL" and position == -1) or (side == "BUY" and position == 1):
        print(f"{symbol}의 포지션을 이미 보유중입니다. ")
        print(f"해당 포지션이 종료될 때까지 대기합니다.\n")
        return False, False

    symbol_price = float(real_time_price(symbol))
    quantity = round(balance / symbol_price, 5)

    # position open을 위한 주문
    paramsMap = {
    "symbol": symbol,
    "side": "BUY" if position == 1 else "SELL",
    "positionSide": "BOTH",
    "type": "MARKET",
    "quantity": quantity
}
    paramsStr = praseParam(paramsMap)
    res = json.loads(send_request(method, path, paramsStr, payload))
    error = res["code"]
    print(f"position open : {error}")
    return quantity, symbol_price
    
def real_time_price(symbol):
    payload = {}
    path = '/openApi/swap/v2/quote/price'
    method = "GET"

    current_time = datetime.now()
    milliseconds = int(current_time.timestamp() * 1000)
    paramsMap = {
        "timestamp": str(milliseconds),
        "symbol": symbol
    }
    paramsStr = praseParam(paramsMap)
    res = json.loads(send_request(method, path, paramsStr, payload))
    return res["data"]["price"]

def user_asset():
    payload = {}
    path = '/openApi/swap/v2/user/balance'
    method = "GET"

    current_time = datetime.now()
    milliseconds = int(current_time.timestamp() * 1000)
    paramsMap = {
        "timestamp": milliseconds,
        "recvWindow": "10000"
    }
    paramsStr = praseParam(paramsMap)
    res = json.loads(send_request(method, path, paramsStr, payload))
    return float(res["data"]["balance"]["balance"])

def send_request(method, path, urlpa, payload):
    signature = hmac.new(SECRETKEY.encode("utf-8"), urlpa.encode("utf-8"), digestmod=sha256).hexdigest()
    url = "%s%s?%s&signature=%s" % (APIURL, path, urlpa, signature)
    headers = {
        'X-BX-APIKEY': APIKEY,
    }
    response = requests.request(method, url, headers=headers, data=payload)
    return response.text

def praseParam(paramsMap):
    sortedKeys = sorted(paramsMap)
    paramsStr = "&".join(["%s=%s" % (x, paramsMap[x]) for x in sortedKeys])
    return paramsStr+"&timestamp="+str(int(time.time() * 1000))


if __name__ == '__main__':
    # wipe_order("ETC-USDT")
    # order("BTC-USDT", 1, 50)
    print(check_positions("BTC-USDT"))