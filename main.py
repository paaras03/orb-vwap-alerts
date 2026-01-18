import os
import time
import requests
import pandas as pd
import pytz
from datetime import datetime, timedelta, time as dtime
from kiteconnect import KiteConnect

requests.post(
    f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage",
    data={
        "chat_id": os.environ["TELEGRAM_CHAT_ID"],
        "text": "TEST MESSAGE: Railway + Telegram working"
    },
    timeout=5
)

# ================= ENV =================
API_KEY = os.environ["KITE_API_KEY"]
ACCESS_TOKEN = os.environ["KITE_ACCESS_TOKEN"]
TG_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TG_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# ================= CONSTANTS =================
TZ = pytz.timezone("Asia/Kolkata")

ORB_START = dtime(9, 15)
ORB_END = dtime(9, 30)
NO_ENTRY_AFTER = dtime(11, 30)

EXIT_ALERT_TIME = dtime(15, 0)
MARKET_CLOSE = dtime(15, 15)

MIN_ORB_PCT = 0.25
RR = 2.0

WATCHLIST = ["TCS", "INFY", "LTIM"]

# ================= UTILS =================
def now():
    return datetime.now(TZ)

def send_telegram(msg):
    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        data={"chat_id": TG_CHAT_ID, "text": msg},
        timeout=5
    )

# ================= KITE =================
kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

inst = pd.DataFrame(kite.instruments("NSE"))
TOKENS = {
    s: int(inst[inst["tradingsymbol"] == s].iloc[0]["instrument_token"])
    for s in WATCHLIST
}

sent_today = set()
market_start_sent = False
exit_alert_sent = False

# ================= MAIN LOOP =================
while True:
    try:
        t = now()

        # -------- BEFORE MARKET --------
        if t.time() < ORB_START:
            time.sleep(30)
            continue

        # -------- MARKET START --------
        if not market_start_sent and t.time() >= ORB_START:
            send_telegram(
                "SYSTEM STARTED\n"
                "Market Open\n"
                f"Watching: {', '.join(WATCHLIST)}"
            )
            market_start_sent = True

        # -------- EXIT REMINDER --------
        if not exit_alert_sent and t.time() >= EXIT_ALERT_TIME:
            send_telegram(
                "EXIT REMINDER\n"
                "Time: 15:00\n"
                "Exit all open intraday positions"
            )
            exit_alert_sent = True

        # -------- MARKET CLOSE --------
        if t.time() >= MARKET_CLOSE:
            send_telegram("MARKET CLOSED\nSystem shutting down")
            break

        # -------- 5-MIN ALIGNMENT --------
        if t.minute % 5 != 0:
            time.sleep(5)
            continue

        for sym, token in TOKENS.items():
            key = (sym, t.date())
            if key in sent_today:
                continue

            candles = kite.historical_data(
                token,
                t - timedelta(days=3),
                t,
                "5minute"
            )

            if len(candles) < 20:
                continue

            df = pd.DataFrame(candles)
            df["date"] = pd.to_datetime(df["date"])
            df["date_only"] = df["date"].dt.date

            day = df[df["date_only"] == t.date()].copy()
            if day.empty:
                continue

            day["time"] = day["date"].dt.time

            # -------- ORB --------
            orb = day[(day["time"] >= ORB_START) & (day["time"] < ORB_END)]
            if orb.empty:
                continue

            orb_high = orb["high"].max()
            orb_low = orb["low"].min()

            if (orb_high - orb_low) / orb_low * 100 < MIN_ORB_PCT:
                continue

            # -------- VWAP --------
            tp = (day["high"] + day["low"] + day["close"]) / 3
            day["vwap"] = (tp * day["volume"]).cumsum() / day["volume"].cumsum()

            last = day.iloc[-2]

            if not (ORB_END < last["time"] <= NO_ENTRY_AFTER):
                continue

            # -------- ENTRY --------
            if last["close"] > orb_high and last["close"] > last["vwap"]:
                sl = max(orb_low, last["vwap"])
                risk = last["close"] - sl
                target = last["close"] + RR * risk

                send_telegram(
                    f"{sym} BUY ALERT\n"
                    f"Time: {last['date'].strftime('%H:%M')}\n"
                    f"Entry: {last['close']:.2f}\n"
                    f"SL: {sl:.2f}\n"
                    f"Target (2R): {target:.2f}"
                )

                sent_today.add(key)

        time.sleep(5)

    except Exception as e:
        send_telegram(f"ERROR: {e}")
        time.sleep(60)
