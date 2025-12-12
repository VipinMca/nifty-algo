import requests
import json

SCRIP_URL = "https://github.com/VipinMca/nifty-algo/releases/tag/algo/scrip_master.json"

def load_scrip_master():
    print("Downloading scrip master…")
    response = requests.get(SCRIP_URL)
    response.raise_for_status()
    return response.json()

scrip_master = load_scrip_master()


def find_token(exch_seg, symbol):
    for item in data:
        if item["exch_seg"] == exch_seg and item["symbol"] == symbol:
            return item["token"]
    return None


# ----------------------------------------
# TEST TOKENS
# ----------------------------------------

print("RELIANCE token =", find_token("NSE", "RELIANCE"))
print("NIFTY FUT token sample:", find_token("NFO", "NIFTY24JANFUT"))

# ----------------------------------------
# FIND NIFTY FUT BY EXPIRY
# ----------------------------------------

def find_nifty_future(expiry_date):
    """
    expiry_date format example: '30JAN2024'
    """
    for item in data:
        if (
            item["exch_seg"] == "NFO"
            and item["instrumenttype"] == "FUTIDX"
            and item["name"] == "NIFTY"
            and item["expiry"] == expiry_date
        ):
            return item["symbol"], item["token"]
    return None, None


symbol, token = find_nifty_future("30JAN2024")
print("Nifty Future Symbol:", symbol)
print("Nifty Future Token:", token)


