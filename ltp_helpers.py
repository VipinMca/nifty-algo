# ltp_helpers.py
"""
Downloads & loads scrip_master.json and provides token lookup helpers.

Usage:
    from ltp_helpers import DATA, find_token, get_equity_token, get_future_token, get_option_token

Environment:
    SCRIP_URL           optional, direct download URL for scrip_master.json (release asset/raw file)
    SCRIP_CACHE_PATH    optional, local cache path (default /tmp/scrip_master.json)
    SCRIP_CACHE_SECONDS optional, cache TTL in seconds (default 24h = 86400)
"""

import os
import json
import time
import requests
from typing import Optional, List, Dict, Any

# Config (override via env)
SCRIP_URL = os.getenv(
    "SCRIP_URL",
    "https://github.com/VipinMca/nifty-algo/releases/download/algo/scrip_master.json"
)
CACHE_PATH = os.getenv("SCRIP_CACHE_PATH", "/tmp/scrip_master.json")
CACHE_TTL = int(os.getenv("SCRIP_CACHE_SECONDS", str(24 * 3600)))  # 24 hours default


def _download_to_cache(url: str, path: str, timeout: int = 60) -> None:
    """Download file (streaming) and write to path. Raises on HTTP error."""
    print("Downloading scrip master…")
    resp = requests.get(url, allow_redirects=True, stream=True, timeout=timeout)
    print("STATUS:", resp.status_code)
    if resp.status_code != 200:
        # show short preview for debugging
        text_preview = resp.text[:500] if hasattr(resp, "text") else "<no text>"
        raise RuntimeError(f"Failed to download scrip master: {resp.status_code}\n{str(text_preview)}")

    # Stream to file
    with open(path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=32768):
            if chunk:
                f.write(chunk)
    # quick verification
    size = os.path.getsize(path)
    print(f"Saved scrip master to {path} ({size} bytes)")


def load_scrip_master(force: bool = False) -> List[Dict[str, Any]]:
    """
    Loads the scrip_master JSON into a Python list.
    Uses a cached file at CACHE_PATH with a TTL of CACHE_TTL seconds.
    Set force=True to re-download regardless of cache age.
    """
    # If cached file exists and is fresh, load it
    if os.path.exists(CACHE_PATH) and not force:
        age = time.time() - os.path.getmtime(CACHE_PATH)
        if age < CACHE_TTL:
            try:
                with open(CACHE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        print(f"Loaded scrip master from cache ({CACHE_PATH}), {len(data)} records")
                        return data
                    # if not list, fallthrough to re-download
            except Exception as e:
                print("Failed to load cache - will re-download:", e)

    # Download fresh copy
    _download_to_cache(SCRIP_URL, CACHE_PATH)

    # Load and return
    with open(CACHE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("scrip_master.json did not contain a JSON array at top level")
    print(f"Loaded scrip master from download, {len(data)} records")
    return data


# Global DATA will be loaded once on import
try:
    DATA = load_scrip_master()
except Exception as e:
    # In case of failure during import, set DATA to empty list but print error.
    print("Warning: could not load scrip_master.json during import:", e)
    DATA = []


# --- Helper utilities for matching --- #
def _norm(s: Optional[str]) -> str:
    return (s or "").strip().upper()


def _matches_symbol(item: Dict[str, Any], symbol: str) -> bool:
    """
    Match input symbol to item. We check 'symbol' and 'name' fields.
    Also allow symbol like 'NIFTY' vs 'Nifty 50' by doing uppercase compare.
    """
    symbol_norm = _norm(symbol)
    if not symbol_norm:
        return False
    # Check common keys
    for key in ("symbol", "name", "tsym"):
        if _norm(item.get(key)) == symbol_norm:
            return True
    # Also allow partial matches: e.g. input "NIFTY" vs "Nifty 50"
    sym = _norm(item.get("symbol"))
    name = _norm(item.get("name"))
    if symbol_norm in sym or symbol_norm in name:
        return True
    return False


def _matches_expiry(item: Dict[str, Any], expiry: Optional[str]) -> bool:
    if not expiry:
        return True
    return (item.get("expiry") or "") == expiry


def _matches_instrumenttype(item: Dict[str, Any], inst: Optional[str]) -> bool:
    if not inst:
        return True
    return _norm(item.get("instrumenttype")) == _norm(inst)


def _matches_strike(item: Dict[str, Any], strike: Optional[float]) -> bool:
    if strike is None:
        return True
    try:
        it_strike = float(item.get("strike", 0) or 0)
        return abs(it_strike - float(strike)) < 1e-6
    except Exception:
        return False


# --- Public API functions --- #
def find_token(exchange: str, symbol: str,
               instrumenttype: Optional[str] = None,
               expiry: Optional[str] = None,
               strike: Optional[float] = None) -> Optional[str]:
    """
    Generic token finder.

    Parameters:
        exchange: 'NSE' etc (compares to item['exch_seg'])
        symbol: symbol/name to match (case-insensitive)
        instrumenttype: optional filter (e.g. 'FUTIDX', 'AMXIDX', 'EQ', 'OPT' etc)
        expiry: optional expiry string (exact match to item['expiry'])
        strike: optional numeric strike (for options)

    Returns:
        token string if found, else None
    """
    ex_norm = _norm(exchange)
    sym_norm = _norm(symbol)

    for item in DATA:
        # check exchange
        if _norm(item.get("exch_seg")) != ex_norm:
            continue

        # symbol match
        if not _matches_symbol(item, sym_norm):
            continue

        # instrument type
        if not _matches_instrumenttype(item, instrumenttype):
            continue

        # expiry
        if not _matches_expiry(item, expiry):
            continue

        # strike
        if not _matches_strike(item, strike):
            continue

        # found
        tok = item.get("token")
        if tok:
            return tok
    return None


def get_equity_token(symbol: str, exchange: str = "NSE") -> Optional[str]:
    """Convenience: find equity token (no expiry, strike)."""
    # instrumenttype for equity may vary; try common ones
    for eq_type in (None, "EQ", "EQSTK"):
        tok = find_token(exchange, symbol, instrumenttype=eq_type)
        if tok:
            return tok
    return None


def get_index_token(name_or_symbol: str, exchange: str = "NSE") -> Optional[str]:
    """Find index token like NIFTY / Nifty 50"""
    # index instrument types: AMXIDX, IDX, INDEX, etc
    for idx_type in (None, "AMXIDX", "IDX", "INDEX"):
        tok = find_token(exchange, name_or_symbol, instrumenttype=idx_type)
        if tok:
            return tok
    return None


def get_future_token(symbol: str, exchange: str = "NSE", expiry: Optional[str] = None) -> Optional[str]:
    """
    Find futures token. If expiry is None, returns the nearest FUT* instrument (first match).
    """
    # try FUTIDX, FUTSTK etc
    for fut_type in ("FUTIDX", "FUTSTK", "FUT"):
        tok = find_token(exchange, symbol, instrumenttype=fut_type, expiry=expiry)
        if tok:
            return tok
    # fallback: any item with symbol match and 'FUT' appearing in instrumenttype
    for item in DATA:
        if _norm(item.get("exch_seg")) != _norm(exchange):
            continue
        if _matches_symbol(item, symbol) and "FUT" in _norm(item.get("instrumenttype")):
            return item.get("token")
    return None


def get_option_token(symbol: str, expiry: str, strike: float, option_type: str, exchange: str = "NSE") -> Optional[str]:
    """
    Find option token by symbol+expiry+strike+option_type.

    option_type should be 'CE' or 'PE' (case-insensitive).
    """
    ot = option_type.upper()
    # common instrument types might include 'OPT', 'CE', 'PE', or 'OPTSTK'
    for item in DATA:
        if _norm(item.get("exch_seg")) != _norm(exchange):
            continue
        if not _matches_symbol(item, symbol):
            continue
        if not _matches_expiry(item, expiry):
            continue
        if not _matches_strike(item, strike):
            continue

        # try to identify CE/PE via instrumenttype, symbol name or other fields
        itype = _norm(item.get("instrumenttype"))
        # some files may store CE/PE in instrumenttype or symbol suffix
        if ot in itype or ot in _norm(item.get("symbol")) or ot in _norm(item.get("name")):
            return item.get("token")

    # fallback: try generic search by matching strike+expiry and CE/PE in symbol/name
    for item in DATA:
        if _norm(item.get("exch_seg")) != _norm(exchange):
            continue
        if not _matches_symbol(item, symbol):
            continue
        if not _matches_expiry(item, expiry):
            continue
        if not _matches_strike(item, strike):
            continue
        if ot in _norm(item.get("symbol")) or ot in _norm(item.get("name")):
            return item.get("token")

    return None


# --- small test / example usage when run as script --- #
if __name__ == "__main__":
    # Quick local tests - adjust symbols and expiry as per your scrip_master
    if not DATA:
        print("No DATA loaded. Exiting.")
        exit(1)

    print("First record sample:", DATA[0])
    print("Trying sample lookups...")
    print("NIFTY (index) token:", get_index_token("NIFTY", "NSE"))
    print("RELIANCE equity token:", get_equity_token("RELIANCE", "NSE"))
    # Example futures and options (you may need to supply expiry / strike in the exact format used in your JSON)
    print("NIFTY future token (nearest):", get_future_token("NIFTY", "NSE"))
    # Example option:
    # print("NIFTY CE token:", get_option_token("NIFTY", "2025-12-26", 24000.0, "CE", "NSE"))

# Exported names
__all__ = [
    "DATA",
    "load_scrip_master",
    "find_token",
    "get_equity_token",
    "get_future_token",
    "get_option_token",
]
