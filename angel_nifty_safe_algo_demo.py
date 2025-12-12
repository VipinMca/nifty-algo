"""
SAFE DEMO VERSION — DOES NOT PLACE REAL ORDERS
Updated: robust handling, uses ltp_helpers DATA if present,
falls back to safe stubs for create_client/get_ltp so script
doesn't fail import-time errors on Railway.
"""

import time
import datetime as dt
import json
import logging, sys
import requests  # for dashboard updates and optional HTTP LTP
import os

# Try to import helpers. ltp_helpers should provide token lookup and optional get_ltp, DATA.
try:
    from ltp_helpers import get_ltp as helper_get_ltp, DATA as SCRIP_DATA, find_token as helper_find_token
except Exception:
    # If ltp_helpers isn't the version you expect, we'll set fallbacks below.
    helper_get_ltp = None
    helper_find_token = None
    SCRIP_DATA = None

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

# Local fallback path (used only if SCRIP_DATA not available)
SCRIP_MASTER_PATH = os.getenv("SCRIP_CACHE_PATH", "/tmp/scrip_master.json")

# Optional backend for status updates
BACKEND_URL = os.getenv("BACKEND_URL", "https://niftybackend-production.up.railway.app/api/update")

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
        requests.post(BACKEND_URL, json=payload, timeout=1)
    except Exception as e:
        # Non-fatal; dashboard is optional
        logger.debug("Dashboard update failed: %s", e)


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
# SCRIP MASTER LOADING (uses ltp_helpers.DATA if available)
# --------------------------------------------
def load_local_master():
    """
    Load from local cache path (fallback). Returns list.
    """
    if not os.path.exists(SCRIP_MASTER_PATH):
        logger.warning("SCRIP_MASTER_PATH not found: %s", SCRIP_MASTER_PATH)
        return []

    try:
        with open(SCRIP_MASTER_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                logger.info("Loaded scrip master from local file: %s (%d records)", SCRIP_MASTER_PATH, len(data))
                return data
            else:
                logger.warning("Local scrip master is not a list.")
                return []
    except Exception as e:
        logger.exception("Failed to load local scrip master: %s", e)
        return []


# Preferred master (from ltp_helpers if present)
if SCRIP_DATA and isinstance(SCRIP_DATA, list) and len(SCRIP_DATA) > 0:
    MASTER = SCRIP_DATA
    logger.info("Using scrip master from ltp_helpers.DATA (%d records)", len(MASTER))
else:
    MASTER = load_local_master()


# Safe find_token wrapper: use helper_find_token if available, else fallback to naive match.
def find_token(exchange, symbol):
    """
    Minimal wrapper compatible with previous calls: find_token("NFO", "NIFTY30DEC24000CE")
    The helper_find_token from ltp_helpers is preferred. If not available we do a simple search.
    """
    # Use provided helper if available
    if helper_find_token:
        try:
            return helper_find_token(exchange, symbol)
        except Exception as e:
            logger.debug("helper_find_token exception: %s", e)

    # Fallback naive search:
    ex_norm = (exchange or "").strip().upper()
    sym_norm = (symbol or "").strip().upper()

    for item in MASTER:
        if (item.get("exch_seg") or "").strip().upper() != ex_norm:
            continue
        # check symbol and name fields (case-insensitive)
        if sym_norm == (item.get("symbol") or "").strip().upper() or sym_norm == (item.get("name") or "").strip().upper():
            return item.get("token")
        # allow partial match (e.g. "NIFTY" in "Nifty 50")
        if sym_norm in (item.get("symbol") or "").upper() or sym_norm in (item.get("name") or "").upper():
            return item.get("token")
    return None


# --------------------------------------------
# GET NIFTY LTP
# --------------------------------------------
# Prefer helper_get_ltp. If not present, use HTTP fallback (best-effort) or return 0.
def get_ltp(client, exchange, symbol, token):
    # If helper exists, delegate
    if helper_get_ltp:
        try:
            return helper_get_ltp(client, exchange, symbol, token)
        except Exception as e:
            logger.debug("helper_get_ltp failed: %s", e)

    # Fallback: try a very small public quote attempt (best-effort)
    # NOTE: This is a best-effort placeholder for demo — replace with broker LTP in production.
    try:
        # Try to parse token -> if token is numeric, we can't fetch public quote reliably
        # So return 0 to avoid crashes.
        logger.debug("Using fallback get_ltp for %s (%s)", symbol, token)
        return 0
    except Exception as e:
        logger.debug("fallback get_ltp error: %s", e)
        return 0


# --------------------------------------------
# COMPUTE NEXT EXPIRY FROM MASTER
# --------------------------------------------
def get_next_expiry_from_master():
    logger.info("DEBUG: Loading expiries from master...")
    expiries = []
    for it in MASTER:
        if it.get("name") == "NIFTY" and it.get("exch_seg") == "NFO":
            exp = it.get("expiry", "")
            if exp and len(exp) in (7, 9):  # allow flexible formats (e.g. 30JAN24 or 30JAN2024)
                expiries.append(exp)

    if not expiries:
        raise Exception("No expiries found in scrip master (NFO NIFTY)")

    # Normalize and sort using try/except
    def parse_exp(e):
        for fmt in ("%d%b%Y", "%d%b%y", "%d%b%Y"):
            try:
                return dt.datetime.strptime(e, fmt).date()
            except Exception:
                continue
        # final fallback: return far future
        return dt.date.max

    expiries_sorted = sorted(set(expiries), key=lambda e: parse_exp(e))
    today = dt.date.today()
    for exp in expiries_sorted:
        d = parse_exp(exp)
        if d >= today:
            logger.info("DEBUG: Selected expiry %s -> %s", exp, d)
            return d

    # if nothing >= today, return the latest available
    last = parse_exp(expiries_sorted[-1])
    logger.info("DEBUG: No future expiry >= today; returning last expiry %s", last)
    return last


# --------------------------------------------
# GET NIFTY LTP wrapper using token if available
# --------------------------------------------
def get_nifty_ltp(client):
    # Try to find NIFTY token from MASTER (prefer name match)
    t = None
    # prefer direct match on 'name' being 'NIFTY' or symbol containing 'NIFTY'
    for item in MASTER:
        if (item.get("exch_seg") or "").upper() == "NSE":
            if (item.get("name") or "").strip().upper() == "NIFTY":
                t = item.get("token")
                sym = item.get("symbol") or "Nifty 50"
                break
            if "NIFTY" in (item.get("symbol") or "").upper():
                t = item.get("token")
                sym = item.get("symbol")
                break

    if not t:
        # fallback to hardcoded token used previously
        logger.debug("NIFTY token not found in MASTER; using fallback token 99926000")
        t = "99926000"
        sym = "Nifty 50"

    return get_ltp(None, "NSE", sym, t)


# --------------------------------------------
# COMPUTE LEGS
# --------------------------------------------
def compute_legs(client):
    nifty = get_nifty_ltp(client)
    logger.info("DEBUG: NIFTY LTP = %s", nifty)

    raw_ce = round_strike(nifty * (1 + STRIKE_DISTANCE_PCT / 100))
    raw_pe = round_strike(nifty * (1 - STRIKE_DISTANCE_PCT / 100))
    raw_he_ce = raw_ce + HEDGE_DISTANCE_PTS
    raw_he_pe = raw_pe - HEDGE_DISTANCE_PTS

    logger.info("DEBUG RAW STRIKES: %s %s %s %s", raw_ce, raw_pe, raw_he_ce, raw_he_pe)

    expiry_date = get_next_expiry_from_master()
    exp_short = expiry_date.strftime("%d%b%y").upper()
    exp_long = expiry_date.strftime("%d%b%Y").upper()
    logger.info("DEBUG EXPIRY: %s %s", exp_short, exp_long)

    # Build available strikes from MASTER
    available = []
    for it in MASTER:
        if it.get("name") == "NIFTY" and it.get("exch_seg") == "NFO":
            if it.get("expiry") == exp_long:
                try:
                    strike_val = int(float(it.get("strike", "0")))
                    available.append(strike_val)
                except:
                    pass

    available = sorted(set(available))
    logger.info("DEBUG AVAILABLE FOR EXPIRY (sample): %s", available[:50])

    if not available:
        raise Exception("No strikes found for expiry")

    # Nearest mapper (available contains strike integers)
    nearest = lambda target: min(available, key=lambda x: abs(x - target))

    # Note: original code used *100 mapping; keep same semantics
    ce_full = nearest(raw_ce * 100)
    pe_full = nearest(raw_pe * 100)
    he_ce_full = nearest(raw_he_ce * 100)
    he_pe_full = nearest(raw_he_pe * 100)

    logger.info("DEBUG MATCHED FULL STRIKES: %s %s %s %s", ce_full, pe_full, he_ce_full, he_pe_full)

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

    # Token assignment using find_token wrapper
    for k, v in legs.items():
        logger.info("DEBUG BUILT SYMBOL: %s", v["symbol"])
        v["token"] = find_token("NFO", v["symbol"])
        logger.info("DEBUG TOKEN LOOKUP: %s → %s", v["symbol"], v["token"])

    logger.info("FINAL LEGS = %s", legs)
    return legs


# --------------------------------------------
# FETCH LTP OF ALL LEGS
# --------------------------------------------
def get_leg_prices(client, legs):
    prices = {}
    for k, v in legs.items():
        tok = v.get("token")
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
                "token": info.get("token"),
                "price": prices.get(name, 0)
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
# create_client fallback (was missing previously)
# --------------------------------------------
# --------------------------------------------
# REAL ANGEL ONE SMARTAPI V2 CLIENT (MPIN + TOTP)
# --------------------------------------------
from smartapi import SmartConnect
import pyotp

def create_client():
    try:
        client_id = os.getenv("CLIENT_ID")
        api_key = os.getenv("API_KEY")
        mpin = os.getenv("MPIN")
        totp_secret = os.getenv("TOTP_SECRET")

        if not all([client_id, api_key, mpin]):
            raise Exception("Missing CLIENT_ID / API_KEY / MPIN environment variables")

        # Generate TOTP (SmartAPI V2 requirement)
        if totp_secret:
            totp = pyotp.TOTP(totp_secret).now()
        else:
            raise Exception("TOTP_SECRET not set for MPIN login")

        # Create smart client
        smart = SmartConnect(api_key)

        # Login using client_id + mpin + totp
        data = smart.generateSessionV2(client_id, mpin, totp)

        jwt_token = data["data"]["jwtToken"]
        refresh_token = data["data"]["refreshToken"]

        smart.setAccessToken(jwt_token)
        smart.setRefreshToken(refresh_token)

        logging.info("🔐 Angel One SmartAPI V2 Login Successful")
        return smart

    except Exception as e:
        logging.error("❌ Angel login failed: %s", e)
        return None

# --------------------------------------------
# RUN
# --------------------------------------------
if __name__ == "__main__":
    # create_client() no longer imported from ltp_helpers; use local (or replace with real)
    client = create_client()
    try:
        run_algo_demo(client)
    except Exception as e:
        logger.exception("Algo crashed: %s", e)




