import requests
import json

SCRIP_URL = "https://github.com/VipinMca/nifty-algo/releases/download/algo/scrip_master.json"

def load_scrip_master():
    print("Downloading scrip master…")
    response = requests.get(SCRIP_URL, allow_redirects=True)
    print("STATUS:", response.status_code)
    print("RAW HEADERS:", response.headers)

    response.raise_for_status()

    # If GitHub returns HTML, show it
    if response.text.strip().startswith("<"):
        print("ERROR: Received HTML instead of JSON")
        print(response.text[:500])
        raise ValueError("Not JSON file content")

    return response.json()

scrip_master = load_scrip_master()
print("FIRST ITEM:", scrip_master[0])
exit()

# data = load_scrip_master()

def find_token(exchange, symbol, instrumenttype=None, expiry=None, strike=None):
    exchange = exchange.upper()
    symbol = symbol.upper()

    for item in scrip_master:
        # Check exchange
        if item.get("exch_seg", "").upper() != exchange:
            continue

        # Check symbol (case-insensitive)
        if item.get("symbol", "").upper() != symbol and item.get("name", "").upper() != symbol:
            continue

        # Optional: instrument type match
        if instrumenttype and item.get("instrumenttype", "").upper() != instrumenttype.upper():
            continue

        # Optional: expiry match
        if expiry and item.get("expiry", "") != expiry:
            continue

        # Optional: strike match
        if strike and float(item.get("strike", "0")) != float(strike):
            continue

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
    for item in scrip_master:
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








