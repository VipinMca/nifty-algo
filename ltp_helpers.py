# ltp_helpers.py

import time
import pyotp
from SmartApi import SmartConnect

# ------------------------------------------------
# CONFIG FILE PATH
# ------------------------------------------------
CONFIG_PATH = r"C:\D Drive\Docs\Trade Script\Options\config.txt"

def load_config():
    config = {}
    with open(CONFIG_PATH, "r") as f:
        for line in f:
            if "=" in line:
                key, val = line.strip().split("=", 1)
                config[key] = val
    return config

cfg = load_config()

API_KEY = cfg.get("API_KEY")
CLIENT_ID = cfg.get("CLIENT_ID")
MPIN = cfg.get("MPIN")
TOTP_SECRET = cfg.get("TOTP_SECRET")

print("DEBUG CONFIG RAW:", cfg)
print("DEBUG CONFIG:", API_KEY, CLIENT_ID, MPIN, TOTP_SECRET)
print("DEBUG TOTP_SECRET:", repr(TOTP_SECRET))


# ------------------------------------------------
# LOGIN FUNCTION
# ------------------------------------------------
def create_client():
    totp = pyotp.TOTP(TOTP_SECRET).now()
    obj = SmartConnect(api_key=API_KEY)

    session = obj.generateSession(CLIENT_ID, MPIN, totp)

    feed_token = obj.getfeedToken()
    print("Login Successful!")
    print("Feed Token:", feed_token)
    print("Refresh Token:", session["data"]["refreshToken"])
    return obj


# ------------------------------------------------
# LTP FUNCTIONS
# ------------------------------------------------
def get_ltp(obj, exchange, tradingsymbol, symboltoken):
    resp = obj.ltpData(exchange, tradingsymbol, symboltoken)
    if resp and resp.get("status"):
        return resp["data"]["ltp"]
    return None


def get_multiple_ltps(obj, symbols):
    results = {}
    for s in symbols:
        results[(s["exchange"], s["tradingsymbol"])] = get_ltp(
            obj, s["exchange"], s["tradingsymbol"], s["symboltoken"]
        )
    return results


def poll_loop(obj, symbols, interval=1):
    while True:
        data = get_multiple_ltps(obj, symbols)
        print("\nLTP Update:", data)
        time.sleep(interval)
