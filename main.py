import time
import os
from datetime import datetime
import requests
import pytz

# ================= CONFIG =================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

ALERT_TITLE = "ORB + VWAP BOT"

IST = pytz.timezone("Asia/Kolkata")

HEARTBEAT_INTERVAL = 3600   # 1 hour
LOOP_SLEEP = 5              # seconds

# ================= TELEGRAM =================
def send_telegram(msg):
    full_msg = f"🔔 {ALERT_TITLE}\n\n{msg}"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": full_msg}
    try:
        r = requests.post(url, json=payload, timeout=10)
        print("Telegram:", r.status_code, full_msg)
    except Exception as e:
        print("Telegram ERROR:", e)

# ================= TIME HELPERS =================
def now_ist():
    return datetime.now(IST)

def is_before_330():
    t = now_ist().time()
    return t < datetime.strptime("15:30", "%H:%M").time()

# ================= MAIN =================
def main():
    send_telegram("🚀 SCRIPT STARTED")

    last_heartbeat = 0

    while True:
        now = time.time()
        now_time = now_ist().strftime("%H:%M:%S")

        # ---- HEARTBEAT (UNCONDITIONAL) ----
        if now - last_heartbeat >= HEARTBEAT_INTERVAL:
            send_telegram(f"💓 HEARTBEAT OK | Time: {now_time}")
            last_heartbeat = now

        # ---- MARKET EXIT CHECK ----
        if not is_before_330():
            send_telegram("🛑 EXITING: Market closed (post 3:30 PM IST)")
            break

        # ---- LOOP TRACE ----
        print(f"Loop alive at {now_time}")
        time.sleep(LOOP_SLEEP)

    send_telegram("✅ SCRIPT EXITED CLEANLY")

if __name__ == "__main__":
    main()
