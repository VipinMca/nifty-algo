"""
ltp_helpers.py
---------------
SmartAPI helper for Railway.
Uses MPIN login only (no password required).
Reads all credentials from Railway environment variables.

Required Railway Variables:
API_KEY
CLIENT_ID
MPIN
TOTP_SECRET (optional)
"""

import os
import logging
import requests
from SmartApi.smartConnect import SmartConnect
import pyotp

# ---------------------------------
# LOGGER
# ---------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ltp_helpers")

# ---------------------------------
# READ ENV VARIABLES
# ---------------------------------
API_KEY     = os.getenv("9nxhRaHH")
CLIENT_ID   = os.getenv("AABW715440")
MPIN        = os.getenv("8266")            # Required
TOTP_SECRET = os.getenv("74WFWMXNZYH7K3FBSJLACY4O2Q")     # Optional

if not API_KEY or not CLIENT_ID or not MPIN:
    logger.error("❌ Missing required environment variables!")
    logger.error("Required: API_KEY, CLIENT_ID, MPIN")
    raise SystemExit("Set Railway variables first.")

# ---------------------------------
# SMARTAPI LOGIN (MPIN-ONLY MODE)
# ---------------------------------
def create_client():
    logger.info("🔐 Logging into SmartAPI via MPIN...")

    try:
        client = SmartConnect(api_key=API_KEY)

        # TOTP for MPIN login if required
        totp_val = pyotp.TOTP(TOTP_SECRET).now() if TOTP_SECRET else None

        session = client.generateSession(CLIENT_ID, MPIN, totp_val)

        if not session or session.get("status") is False:
            logger.error("❌ SmartAPI MPIN login failed: %s", session)
            raise SystemExit("SmartAPI MPIN login failed")

        logger.info("✅ SmartAPI MPIN login successful.")
        return client

    except Exception as e:
        logger.exception("SmartAPI MPIN Login Error:")
        raise SystemExit(f"SmartAPI MPIN Login Error: {e}")

# ---------------------------------
# SAFE LTP FETCH
# ---------------------------------
def get_ltp(client, exchange, tradingsymbol, token):
    try:
        body = {
            "exchange": exchange,
            "tradingsymbol": tradingsymbol,
            "symboltoken": str(token)
        }

        url = "https://apiconnect.angelone.in/rest/secure/angelbroking/order/v1/getLtpData"

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-PrivateKey": API_KEY,
            "X-SourceID": "WEB",
            "X-UserType": "USER",
            "X-ClientLocalIP": "127.0.0.1",
            "X-ClientPublicIP": "127.0.0.1",
            "X-MACAddress": "00:00:00:00:00:00"
        }

        r = requests.post(url, json=body, headers=headers, timeout=5)
        data = r.json()

        if not data.get("status"):
            logger.warning(f"LTP ERROR for {tradingsymbol}: {data}")
            return None

        return data["data"]["ltp"]

    except Exception as e:
        logger.warning(f"LTP fetch failed for {tradingsymbol}: {e}")
        return None


# ---------------------------------
# TEST (optional)
# ---------------------------------
if __name__ == "__main__":
    print("Testing MPIN SmartAPI login...")
    c = create_client()
    print("Login OK!")
    nifty = get_ltp(c, "NSE", "Nifty 50", "99926000")
    print("NIFTY LTP =", nifty)
