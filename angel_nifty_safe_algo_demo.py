"""
SAFE DEMO VERSION — DOES NOT PLACE REAL ORDERS
Works with SmartAPI + ltp_helpers.py + scrip_master.json.
Provides live updates to a Web Dashboard via /api/update.
"""

import time
import datetime as dt
import json
import logging, sys
import requests  # <-- Added for dashboard updates

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

SCRIP_MASTER_PATH = r"C:\D Drive\Docs\Trade Script\Options\scrip_master.json"


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
        BACKEND_URL = "https://niftybackend-production.up.railway.app/api/update"
        requests.post(BACKEND_URL, json=payload, timeout=0.5)
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
# FETCH NEXT EXPIRY FROM MASTER
# --------------------------------------------
def get_next_expiry_from_master():
    print("\nDEBUG: Loading expiries from master...")

    with open(SCRIP_MASTER_PATH, "r") as f:
        data = json.load(f)

    expiries = []
    for it in data:
        if it.get("name") == "NIFTY" and it.get("exch_seg") == "NFO":
            exp = it.get("expiry", "")
            if len(exp) == 9:  # DDMMMYYYY
                expiries.append(exp)

    expiries = sorted(set(expiries), key=lambda e: dt.datetime.strptime(e, "%d%b%Y"))

    today = dt.date.today()
    for exp in expiries:
        d = dt.datetime.strptime(exp, "%d%b%Y").date()
        if d >= today:
            print("DEBUG: Selected Expiry =", exp)
            return d

    raise Exception("No future expiry found in scrip master.")


# --------------------------------------------
# GET NIFTY LTP
# --------------------------------------------
def get_nifty_ltp(client):
    symbol = "Nifty 50"
    token = "99926000"
    return get_ltp(client, "NSE", symbol, token)


# --------------------------------------------
# COMPUTE LEGS
# --------------------------------------------
def compute_legs(client):
    nifty = get_nifty_ltp(client)
    print("\nDEBUG: NIFTY LTP =", nifty)

    raw_ce = round_strike(nifty * (1 + STRIKE_DISTANCE_PCT / 100))
    raw_pe = round_strike(nifty * (1 - STRIKE_DISTANCE_PCT / 100))
    raw_he_ce = raw_ce + HEDGE_DISTANCE_PTS
    raw_he_pe = raw_pe - HEDGE_DISTANCE_PTS

    print("DEBUG RAW STRIKES:", raw_ce, raw_pe, raw_he_ce, raw_he_pe)

    expiry_date = get_next_expiry_from_master()
    exp_short = expiry_date.strftime("%d%b%y").upper()
    exp_long = expiry_date.strftime("%d%b%Y").upper()
    print("DEBUG EXPIRY:", exp_short, exp_long)

    # Load strikes from master
    with open(SCRIP_MASTER_PATH, "r") as f:
        data = json.load(f)

    available = []
    for it in data:
        if it.get("name") == "NIFTY" and it.get("exch_seg") == "NFO":
            if it.get("expiry") == exp_long:
                try:
                    strike_val = int(float(it.get("strike", "0")))
                    available.append(strike_val)
                except:
                    pass

    available = sorted(set(available))
    print("DEBUG AVAILABLE FOR EXPIRY (sample):", available[:50])

    if not available:
        raise Exception("No strikes found for expiry")

    # Nearest real strike mapper
    nearest = lambda target: min(available, key=lambda x: abs(x - target))

    ce_full = nearest(raw_ce * 100)
    pe_full = nearest(raw_pe * 100)
    he_ce_full = nearest(raw_he_ce * 100)
    he_pe_full = nearest(raw_he_pe * 100)

    print("DEBUG MATCHED FULL STRIKES:", ce_full, pe_full, he_ce_full, he_pe_full)

    def make_symbol(full, opt):
        short_strike = full // 100  # 2595000 → 25950
        opt = "CE" if "C" in opt.upper() else "PE"
        return f"NIFTY{exp_short}{short_strike}{opt}"

    legs = {
        "sell_ce": {"exchange": "NFO", "symbol": make_symbol(ce_full, "CE"), "full": ce_full},
        "sell_pe": {"exchange": "NFO", "symbol": make_symbol(pe_full, "PE"), "full": pe_full},
        "buy_ce": {"exchange": "NFO", "symbol": make_symbol(he_ce_full, "CE"), "full": he_ce_full},
        "buy_pe": {"exchange": "NFO", "symbol": make_symbol(he_pe_full, "PE"), "full": he_pe_full},
    }

    # Token assignment
    for k, v in legs.items():
        print("DEBUG BUILDED SYMBOL:", v["symbol"])
        v["token"] = find_token("NFO", v["symbol"])
        print(f"DEBUG TOKEN LOOKUP: {v['symbol']} → {v['token']}")

    print("\nFINAL LEGS =", legs)
    return legs


# --------------------------------------------
# FETCH LTP OF ALL LEGS
# --------------------------------------------
def get_leg_prices(client, legs):
    prices = {}
    for k, v in legs.items():
        tok = v["token"]
        if not tok:
            prices[k] = 0
            continue
        l = get_ltp(client, v["exchange"], v["symbol"], tok)
        prices[k] = l if l is not None else 0
    return prices


# --------------------------------------------
# DEMO ENTRY & EXIT
# --------------------------------------------
entry_prices = {}

def demo_entry(legs, prices):
    global entry_prices
    entry_prices = prices
    net_credit = (prices["sell_ce"] + prices["sell_pe"]) - (prices["buy_ce"] + prices["buy_pe"])
    logger.info("\n🟢 DEMO ENTRY")
    logger.info(f"Entry Prices: {prices}")
    logger.info(f"Net Credit: {net_credit}")
    return net_credit


def demo_exit(legs, prices, note):
    pnl = ((entry_prices["sell_ce"] - prices["sell_ce"]) +
           (entry_prices["sell_pe"] - prices["sell_pe"]) -
           (entry_prices["buy_ce"] - prices["buy_ce"]) -
           (entry_prices["buy_pe"] - prices["buy_pe"]))

    logger.info("\n🔴 DEMO EXIT")
    logger.info(f"Reason: {note}")
    logger.info(f"Exit Prices: {prices}")
    logger.info(f"PnL: {pnl}")
    logger.info("-" * 50)


# --------------------------------------------
# MAIN LOOP
# --------------------------------------------
def run_algo_demo(client):
    wait_until(*ENTRY_TIME)

    legs = compute_legs(client)
    prices = get_leg_prices(client, legs)
    initial_credit = demo_entry(legs, prices)

    target = initial_credit * 0.65
    sl = initial_credit * -0.5

    logger.info(f"Target: {target}, SL: {sl}")

    while True:
        now = dt.datetime.now()
        if now.hour > EXIT_TIME[0] or (now.hour == EXIT_TIME[0] and now.minute >= EXIT_TIME[1]):
            prices = get_leg_prices(client, legs)
            demo_exit(legs, prices, "TIME EXIT")
            return

        prices = get_leg_prices(client, legs)
        net_credit = (prices["sell_ce"] + prices["sell_pe"]) - (prices["buy_ce"] + prices["buy_pe"])
        pnl = net_credit - initial_credit

        logger.info(f"Loop → Credit: {net_credit}, PnL: {pnl}")

        # Prepare dashboard-friendly leg structure
        nft = get_nifty_ltp(client)
        legs_display = {
            name: {
                "symbol": info["symbol"],
                "token": info["token"],
                "price": prices[name]
            }
            for name, info in legs.items()
        }

        # --- Update dashboard ---
        push_status(
            nifty_ltp=nft,
            legs=legs_display,
            prices=prices,
            net_credit=net_credit,
            pnl=pnl,
            logs=[f"Loop credit={net_credit}, pnl={pnl}"]
        )

        # Exit conditions
        if net_credit <= target:
            demo_exit(legs, prices, "TARGET HIT")
            return

        if pnl <= sl:
            demo_exit(legs, prices, "STOPLOSS HIT")
            return

        time.sleep(POLL_INTERVAL)


# --------------------------------------------
# RUN
# --------------------------------------------
if __name__ == "__main__":
    client = create_client()
    run_algo_demo(client)

