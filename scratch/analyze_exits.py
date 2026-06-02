import os
import requests
import sys
from dotenv import load_dotenv

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend", ".env"))
BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY", "")

# The tokens that dumped
tokens = ["1b", "GAYBRO", "SOLANA", "MCDOGE", "FCM", "CHIMP", "SolanaLife", "RCL", "ANTH", "onboard", "BULL"]

def search_token_address(symbol):
    url = f"https://public-api.birdeye.so/defi/v3/search?keyword={symbol}&chain=solana"
    headers = {"X-API-KEY": BIRDEYE_API_KEY, "Accept": "application/json"}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            items = data.get("data", {}).get("items", [])
            for item in items:
                if item.get("type") == "token" and item.get("symbol", "").lower() == symbol.lower():
                    return item.get("address")
    except Exception:
        pass
    return None

def get_token_overview(address):
    url = f"https://public-api.birdeye.so/defi/token_overview?address={address}"
    headers = {"X-API-KEY": BIRDEYE_API_KEY, "Accept": "application/json"}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            return r.json().get("data", {})
    except Exception:
        pass
    return {}

def main():
    print("=" * 80)
    print("🔍 INVESTIGASI KOIN PECUNDANG (-15% DUMP)")
    print("=" * 80)
    print(f"{'SYMBOL':<15} | {'LIQUIDITY':<12} | {'MCAP':<12} | {'LIQ/MC%':<10}")
    print("-" * 80)
    
    for sym in tokens:
        addr = search_token_address(sym)
        if addr:
            ov = get_token_overview(addr)
            liq = ov.get("liquidity", 0) or 0
            mc = ov.get("mc", 0) or 0
            ratio = (liq / mc * 100) if mc > 0 else 0
            print(f"{sym:<15} | ${liq:<11.0f} | ${mc:<11.0f} | {ratio:.1f}%")
        else:
            print(f"{sym:<15} | NOT FOUND")

if __name__ == "__main__":
    main()
