import requests
import json

SCRIP_URL = "https://github.com/VipinMca/nifty-algo/releases/download/algo/scrip_master.json"


# ------------------------------
# LOAD JSON (with redirect + HTML check)
# ------------------------------
def load_scrip_master():
    print("Downloading scrip master…")
    response = requests.get(SCRIP_URL, allow_redirects=True)
    print("STATUS:", response.status_code)
    print("RAW HEADERS:", response.headers)

    response.raise_for_status()

    # Detect HTML (bad URL or redirect)
    if response.text.strip().startswith("<"):
        print("ERROR: Received HTML instead of JSON")
        print(response.text[:500])
        raise ValueError("Not JSON file content")

    return response.json()


data = load_scrip_master()
print("FIRST ITEM:", data[0])


# Normalize strings
def norm(x):
    return (x or "").strip().upper()


# ------------------------------
# FLEXIBLE TOKEN FINDER
# ------------------------------
def find_token(exchange, symbol, instrumenttype=None, expiry=None, strike=None):
    ex = norm(exchange)
    sym = norm(symbol)

    for item in data:

        # Exchange match
        if norm(item.get("exch_seg")) != ex:
            continue

        # Symbol match (symbol OR name OR partial match)
        if (
            sym != norm(item.get("symbol")) and
            sym != norm(item.get("name")) and
            sym not in norm(item.get("symbol")) and
            sym not in norm(item.get("name"))
        ):
            continue

        # Instrument type
        if instrumenttype and norm(item.get("instrumenttype")) != norm(instrumenttype):
            continue

        # Expiry
        if expiry and item.get("expiry") != expiry:
            continue

        # Strike
        if strike:
            try:
                if float(item.get("strike", 0)) != float(strike):
                    continue
            except:
                continue

        return item["token"]

    return None


# ------------------------------
# TEST CASES
# ------------------------------

print("\n--- TEST CASES ---")

print("INDEX: NIFTY token =", find_token("NSE", "NIFTY"))

print("INDEX: NIFTY 50 token =", find_token("NSE", "Nifty 50"))

print("EQUITY: RELIANCE token =", find_token("NSE", "RELIANCE"))

print("Trying generic NIFTY future match:")
print("Token:", find_token("NFO", "NIFTY", instrumenttype="FUTIDX"))


# ------------------------------
# Specific future finder
# ------------------------------
def find_nifty_future(expiry_date):
    """
    expiry_date must match EXACT JSON expiry format
    """
    for item in data:
        if (
            norm(item.get("exch_seg")) == "NFO" and
            norm(item.get("instrumenttype")) == "FUTIDX" and
            norm(item.get("name")) == "NIFTY" and
            item.get("expiry") == expiry_date
        ):
            return item.get("symbol"), item.get("token")
    return None, None


symbol, token = find_nifty_future("30JAN2024")
print("Nifty Future Symbol:", symbol)
print("Nifty Future Token:", token)
