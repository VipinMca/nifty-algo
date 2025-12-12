"""
SAFE DEMO VERSION — DOES NOT PLACE REAL ORDERS
Works with SmartAPI + ltp_helpers.py + scrip_master.json.
Provides live updates to a Web Dashboard via /api/update.
"""

import time
import datetime as dt
import json
import logging, sys
import requests

from ltp_helpers import create_client, get_ltp
from find_token import find_token

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger()

# --------------------------------------------
# CONFIG
# --------------------------------------------
UNDERLYING = "NIFTY"
ENTRY_TIME = (9, 25)
EXIT_TIME = (15, 15)
STRIKE_DISTANCE_PCT = 0.5
HEDGE_DISTANCE_PTS = 100
ROUND = 50
POLL_INTERVAL = 5
LIVE = False  # DEMO ONLY

SCRIP_MASTER_PATH = "/app/scrip_master.json"  # Railway-friendly path


# --------------------------------------------
# SEND STATUS TO WEB DASHBOARD
# --------------------------------------------
def push_status(nifty_ltp, legs, prices, net_credit, pnl, logs):
    try:
        payload = {
            "timestamp": dt.datetime.now().isoformat(),
            "nifty_ltp": nifty_ltp,
            "legs": legs,
            "net_credit": net_credit,
            "pnl": pnl,
            "logs": logs[-30:]
        }
        requests.post("http://localhost:5000/api/update", json=payload, timeout=0.5)
    except Exception as e:
        print("Dashboard update failed:", e)


# --------------------------------------------
# HELPERS
# --------------------------------------------
def round_strike(x):
    return int(round(x / ROUND) * ROUND)


def wait_until(h, m):
    logger.info(f"⏳ Waiting until {h}:{m} ...")
    while True:
        now = dt.datetime.now()
        if now.hour > h or (now.hour == h and now.minute >= m):
            break
        time.sleep(2)


# --------------------------------------------
# FETCH NEXT EXP
