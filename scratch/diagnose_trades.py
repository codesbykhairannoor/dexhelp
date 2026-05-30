import sys
import os
import requests
import json

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(os.path.dirname(CURRENT_DIR), "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from dex_hunter import check_token_security

symbols = ["perpfun", "TRYHARDS", "Scalpoor", "goy", "iMoney", "Retail", "noop", "Shizuku", "BOO"]

def find_mint_address(symbol):
    try:
        url = f"https://api.dexscreener.com/latest/dex/search?q={symbol}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            pairs = data.get("pairs", [])
            for p in pairs:
                if p.get("chainId") == "solana":
                    base_token = p.get("baseToken", {})
                    # Double check symbol match case-insensitively
                    if base_token.get("symbol", "").lower() == symbol.lower():
                        return base_token.get("address"), p.get("priceUsd")
            # If no perfect match, return first solana pair base address
            for p in pairs:
                if p.get("chainId") == "solana":
                    return p.get("baseToken", {}).get("address"), p.get("priceUsd")
    except Exception as e:
        print(f"Error searching {symbol}: {e}")
    return None, None

def diagnose():
    print("=" * 80)
    print("[DIAGNOSTIC] RUNNING DIAGNOSTIC ON TRADED TOKENS")
    print("=" * 80)
    
    for sym in symbols:
        print(f"\nSearching for {sym}...")
        address, price = find_mint_address(sym)
        if not address:
            print(f"❌ Could not find address for {sym}")
            continue
            
        print(f"Found address: {address} (Price: ${price})")
        res = check_token_security("solana", address)
        print(f"Result for {sym}:")
        print(f"  Status       : {res['status']}")
        print(f"  Flags        : {res['flags']}")
        print(f"  Score Impact : {res['score_impact']}")

if __name__ == "__main__":
    diagnose()
