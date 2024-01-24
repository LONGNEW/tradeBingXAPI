import schedule
import time
import temp_macd_bingX
import temp_bingx
import temp_bollinger_bingX
import Gmail
import sys
from datetime import datetime, timedelta, timezone
from firebase_admin import db

# 기준
# 익절 현물 2%, 손절 현물 1%
TRADE_cnt = db.reference("/TRADE_cnt").get()
MACD_ETH_cnt = db.reference("MACD/MACD_ETH_cnt").get()
MACD_BTC_cnt = db.reference("MACD/MACD_BTC_cnt").get()

BB_ETH_cnt = db.reference("BB/BB_ETH_cnt").get()
BB_BTC_cnt = db.reference("BB/BB_BTC_cnt").get()

start_balance = db.reference("/start_balance").get()

# argument로 입력 받기
leverage = db.reference("/leverage").get()

balance = db.reference("/trade_balance").get()
earn_percen = 2.15
loss_percen = 1

def kor_time():
    current_time = datetime.now()
    current_time_utc = current_time.astimezone(timezone.utc)
    current_time_kst = current_time_utc + timedelta(hours=9)
    formatted_time = current_time_kst.strftime("%Y-%m-%d %H:%M:%S")
    return formatted_time

def eth_MACD():
    target_symbol = "ETH-USDT"

    # 1. MACD 계산
    print(f"현재 시간: {kor_time()}, {target_symbol} MACD 체킹 시작")
    flag1 = temp_macd_bingX.check_macd(target_symbol)

    # 3. flag True면 주문 하기.
    golden = "GOLD"
    dead = "DEAD"
    if flag1 != 0:
        print(f"{target_symbol}에서 {golden if flag1 == 1 else dead} Cross 발생!")

        # balance = (int(db.reference("/now_balance").get()) // 2) * leverage
        print(f"총 {balance}$만큼의 주문 시작!")
        temp_bingx.wipe_order(target_symbol)
        qty, symbol_price = temp_bingx.order(target_symbol, flag1, balance)
        if not qty and not symbol_price:
            # 이미 포지션을 보유하고 있는 중으로 주문을 하지 않음.
            return 0

        temp_bingx.set_SL(target_symbol, flag1, qty, symbol_price, loss_percen)
        temp_bingx.set_TP(target_symbol, flag1, qty, symbol_price, earn_percen)
        print("주문 완료!\n")

        db.reference().update({"MACD/ETH_pos": 1})
        Gmail.send_email(f"BingX: {target_symbol} 포지션 오픈 완료 {golden if flag1 == 1 else dead} Cross 발생!")
        return 1
    else:
        print("조건 불만족...\n")
        return 0

def btc_MACD():
    target_symbol = "BTC-USDT"

    # 1. MACD 계산
    print(f"현재 시간: {kor_time()}, {target_symbol} MACD 체킹 시작")
    flag1 = temp_macd_bingX.check_macd(target_symbol)

    # 3. flag True면 주문 하기.
    golden = "GOLD"
    dead = "DEAD"
    if flag1 != 0:
        print(f"{target_symbol}에서 {golden if flag1 == 1 else dead} Cross 발생!")

        # balance = (int(db.reference("/now_balance").get()) // 2) * leverage
        print(f"총 {balance}$만큼의 주문 시작!\n")
        temp_bingx.wipe_order(target_symbol)
        qty, symbol_price = temp_bingx.order(target_symbol, flag1, balance)
        if not qty and not symbol_price:
            # 이미 포지션을 보유하고 있는 중으로 주문을 하지 않음.
            return 0

        temp_bingx.set_SL(target_symbol, flag1, qty, symbol_price, loss_percen)
        temp_bingx.set_TP(target_symbol, flag1, qty, symbol_price, earn_percen)
        print("주문 완료!\n")

        db.reference().update({"MACD/BTC_pos": 1})
        Gmail.send_email(f"BingX: {target_symbol} 포지션 오픈 완료 {golden if flag1 == 1 else dead} Cross 발생!")
        return 1
    else:
        print("조건 불만족...\n")
        return 0

def eth_BB():
    target_symbol = "ETH-USDT"
    print(f"현재 시간: {kor_time()}, {target_symbol} BB 체킹 시작")
    # balance = (int(db.reference("/now_balance").get()) // 2) * leverage
    return temp_bollinger_bingX.buy_or_sell(target_symbol, balance, "4h")

def btc_BB():
    target_symbol = "BTC-USDT"
    print(f"현재 시간: {kor_time()}, {target_symbol} BB 체킹 시작")
    # balance = (int(db.reference("/now_balance").get()) // 2) * leverage
    return temp_bollinger_bingX.buy_or_sell(target_symbol, balance, "4h")

def job():
    global MACD_ETH_cnt, MACD_BTC_cnt
    global BB_ETH_cnt, BB_BTC_cnt
    global TRADE_cnt
    print(f"현재 시간: {kor_time()}")

    TRADE_cnt += 1
    do_MACD = db.reference("do_MACD").get()

    set_leverage_ETH = temp_bingx.switch_levarage("ETH-USDT", leverage)
    set_leverage_BTC = temp_bingx.switch_levarage("BTC-USDT", leverage)

    # BB_ETH_cnt += eth_BB()
    # BB_BTC_cnt += btc_BB()

    # BB_ETH_pos = db.reference("BB/ETH_pos").get()
    # BB_BTC_pos = db.reference("BB/BTC_pos").get()
    #if do_MACD == "do" and BB_ETH_pos == 0:
        #MACD_ETH_cnt += eth_MACD()
    # if do_MACD == "do" and BB_BTC_pos == 0:
    #     MACD_BTC_cnt += btc_MACD()

    # check double BB
    print("-----------------------------------------------")
    for symbol in ["BTC-USDT", "ETH-USDT", "SOL-USDT",
                   "ORDI-USDT", "MASK-USDT",
                   "NEAR-USDT", "ICP-USDT"]:
        Up_20, _, Low_20 = temp_bollinger_bingX.check_bollinger(symbol, "1h", before=-1)
        Up_4, _, Low_4 = temp_bollinger_bingX.check_bollinger(symbol, "1h", 4, 4, before=-1)
        price_data = temp_bollinger_bingX.only_1_prices(symbol, "1h")[0]
        high, low = float(price_data["high"]), float(price_data["low"])

        decimal_places1 = len(str(high).split('.')[-1])
        decimal_places2 = len(str(low).split('.')[-1])

        # 두 숫자 중 더 많은 소수점 위치로 반올림
        decimal_cnt = max(decimal_places1, decimal_places2) - 1
        high, low = round(high, decimal_cnt), round(low, decimal_cnt)
        Up_20, Low_20 = round(Up_20, decimal_cnt), round(Low_20, decimal_cnt)
        Up_4, Low_4 = round(Up_4, decimal_cnt), round(Low_4, decimal_cnt)
        print(f"{symbol}의 double BB")
        print(f"4, 4와 상한 비교 {Up_4 <= high}: {Up_20}, {Up_4}, {high}")
        print(f"4, 4와 하한 비교 {low <= Low_4}: {Low_20}, {Low_4}, {low}")

        if Up_4 <= high and low <= Low_4:
            print(f"조건 만족하여 이메일 전송!!!\n")
            Gmail.send_email(f"BingX: {symbol}에서 BB length 4의 상, 하한을 동시에 찌르는 상황 발생!")
            continue
            
        if Up_4 <= high:
            print(f"{symbol}에서 BB length 4의 상한을 찌르는 상황 발생!")
            # qty, symbol_price = temp_bingx.order(symbol, -1, balance)
            # temp_bingx.set_SL(symbol, -1, qty, symbol_price, loss_percen)
            Gmail.send_email(f"BingX: {symbol}에서 BB length 4의 상한을 찌르는 상황 발생!")
            continue
            
        if low <= Low_4:
            print(f"{symbol}에서 BB length 4의 상한을 찌르는 하한을 발생!")
            # qty, symbol_price = temp_bingx.order(symbol, 1, balance)
            # temp_bingx.set_SL(symbol, 1, qty, symbol_price, loss_percen)
            Gmail.send_email(f"BingX: {symbol}에서 BB length 4의 하한을 찌르는 상황 발생!")
            continue
            
        print(f"조건 불만족...\n")
    print("-----------------------------------------------\n")
    db.reference().update({"TRADE_cnt":TRADE_cnt})
    db.reference().update({"MACD/MACD_BTC_cnt": MACD_BTC_cnt})
    db.reference().update({"MACD/MACD_ETH_cnt": MACD_ETH_cnt})
    db.reference().update({"BB/BB_ETH_cnt": BB_ETH_cnt})
    db.reference().update({"BB/BB_BTC_cnt": BB_BTC_cnt})


def status():
    print(f"현재 시간: {kor_time()},  MACD + BB 거래 시도 횟수: {TRADE_cnt}")
    print(f"BB_BTC 주문 횟수: {BB_BTC_cnt}회, BB_ETH 주문 횟수: {BB_ETH_cnt}")
    print(f"MACD_BTC 주문 횟수: {MACD_BTC_cnt}회, MACD_ETH 주문 횟수: {MACD_ETH_cnt}\n")

    BB_ETH_pos = db.reference("BB/ETH_pos").get()
    BB_BTC_pos = db.reference("BB/BTC_pos").get()
    MACD_ETH_pos = db.reference("MACD/ETH_pos").get()
    MACD_BTC_pos = db.reference("MACD/BTC_pos").get()
    # print(f"현재 포지션 여부")
    # print(f"BB_BTC: {BB_BTC_pos}, BB_ETH: {BB_ETH_pos}")
    # print(f"MACD_BTC: {MACD_BTC_pos}, MACD_ETH: {MACD_ETH_pos}\n")

    now_balance = temp_bingx.user_asset()
    ratio = ((now_balance - start_balance) / start_balance) * 100
    print(f"시작 금액: {start_balance}, 현재 금액: {now_balance}, 레버리지: {leverage}x")
    print(f"수익률: {round(ratio, 5)}%\n")

    db.reference().update({"now_balance": now_balance})

# 15분마다 정각에 job 함수를 실행
schedule.every().hour.at("15:10").do(job)
schedule.every().hour.at("30:10").do(job)
schedule.every().hour.at("45:10").do(job)
schedule.every().hour.at("00:10").do(job)

schedule.every().hour.at("15:30").do(status)
print(f"설정 레버리지: {leverage}x, 설정 balance: {balance}")
print(f"거래시작! \n")

while True:
    schedule.run_pending()
    time.sleep(10)
