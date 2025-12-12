import os
import json
import time
import requests
import pyotp
import logging

from smartapi import SmartConnect

logger = logging.getLogger(__name__)

SCRIP_MASTER_URL = "https://github.com/VipinMca/nifty-algo/releases/download/algo/scrip_master.json"
LOCAL_SCRIP_PATH = "/app/scrip_master.json"


# ---------------------------------------------------------
# LOAD SCRIP MASTER (local or download)
# ---------------------------------------------------------
def load_scrip_master():
    """Load scrip master from local file or download."""
    if os.path.exists(LOCAL_SCRIP_PATH):
        try:
            with open(LOCAL_SCRIP_PATH, "r") as f:
                data = json.load(f)
            logger.info(f"Loaded scrip master from local file: {LOCAL_SCRIP_PATH} ({len(data)} records)")
            return data
        except:
            pass

    logger.info("Downloading scrip master…")
    response = requests.get(SCRIP_MASTER_URL)
    response.raise_for_status()
    data = response.json()

    with open(LOCAL_SCRIP_PATH, "w") as f:
        json.dump(data, f)

    logger.info(f"Saved scrip master locally: {LOCAL_SCRIP_PATH}")
    return data


# ---------------------------------------------------------
# SMARTAPI LOGIN (MPIN/TOTP)
# ---------------------------------------------------------
def create_client():
    """Create SmartAPI client using MPIN login."""
    logger.info("🔐 Starting SmartAPI MPIN Login...")

    API_KEY = os.getenv("API_KEY")
    CLIENT_ID = os.getenv("CLIENT_ID")     # Angel One clientcode
    MPIN = os.getenv("MPIN")               # MPIN (4 or 6 digits)
    TOTP_SECRET = os.getenv("TOTP_SECRET")

    if not API_KEY or not CLIENT_ID or not MPIN or not TOTP_SECRET:
        logger.error("❌ Missing required env variables: API_KEY, CLIENT_ID, MPIN, TOTP_SECRET")
        return None

    # Generate TOTP
    try:
        totp = pyotp.TOTP(TOTP_SECRET).now()
    except:
        logger.error("❌ Invalid TOTP secret")
        return None

    # SmartAPI object (from your `smartapi/` folder)
    try:
        smart = SmartConnect(api_key=API_KEY)
    except Exception as e:
        logger.error(f"❌ Failed to initialize SmartConnect: {e}")
        return None

    # Try login
    try:
        response = smart.generateSessionV2(CLIENT_ID, MPIN, totp)
        logger.info("🔐 RAW LOGIN RESPONSE:")
        logger.info(response)

        # Assign tokens
        jwt = response["data"]["jwtToken"]
        refresh = response["data"]["refreshToken"]

        smart.setAccessToken(jwt)
        smart.setRefreshToken(refresh)

        logger.info("✅ SmartAPI MPIN Login Successful!")
        return smart

    except Exception as e:
        logger.error(f"❌ SmartAPI MPIN Login Failed: {e}")
        return None


# ---------------------------------------------------------
# GET LTP
# ---------------------------------------------------------
def get_ltp(client, exchange, symbol, token):
    """Fetch LTP safely via SmartAPI."""
    if client is None:
        logger.error("❌ LTP request failed → client is None")
        return None

    try:
        payload = {
            "exchange": exchange,
            "tradingsymbol": symbol,
            "symboltoken": token
        }
        response = requests.post(
            "https://apiconnect.angelone.in/rest/secure/angelbroking/market/v1/quote",
            json={"mode": "LTP", "exchangeTokens": {exchange: [token]}},
            headers={
                "Authorization": f"Bearer {client.jwt_token}",
                "Content-Type": "application/json",
                "X-SourceID": "WEB",
                "X-ClientLocalIP": "127.0.0.1",
                "X-ClientPublicIP": "127.0.0.1",
                "X-MACAddress": "AA-BB-CC-11-22-33",
                "Accept": "application/json"
            }
        )

        data = response.json()
        ltp = data["data"][exchange][0]["ltp"]
        return float(ltp)

    except Exception as e:
        logger.error(f"❌ LTP error for {symbol}/{token}: {e}")
        return None


# ---------------------------------------------------------
# GLOBAL SCRIP MASTER LOADED ON IMPORT
# ---------------------------------------------------------
try:
    SCRIP_MASTER = load_scrip_master()
except Exception as e:
    logger.error(f"❌ Failed to load scrip master: {e}")
    SCRIP_MASTER = []
