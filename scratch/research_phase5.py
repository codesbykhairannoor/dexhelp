import requests
import json
import time
import sys

# Fix encoding
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

winners = ["STRAIGHT", "KEKIUS", "PIE", "GOLEM", "Liquititty"]
losers = ["1b", "GAYBRO", "SOLANA", "MCDOGE", "FCM", "CHIMP", "SolanaLife", "RCL", "ANTH", "onboard", "BULL"]

def search_dexscreener(symbol):
    try:
        url = f"https://api.dexscreener.com/latest/dex/search?q={symbol}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            pairs = r.json().get("pairs", [])
            # Filter pairs on Solana and created within last 4 days (4 * 24 * 3600 * 1000)
            now_ms = int(time.time() * 1000)
            recent_pairs = []
            for p in pairs:
                if p.get("chainId") == "solana":
                    created = p.get("pairCreatedAt", 0)
                    if created > 0 and (now_ms - created) < (4 * 24 * 3600 * 1000):
                        if p.get("baseToken", {}).get("symbol", "").lower() == symbol.lower():
                            recent_pairs.append(p)
            
            if recent_pairs:
                # Return the one with highest liquidity to avoid dead clones
                recent_pairs.sort(key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0), reverse=True)
                return recent_pairs[0]
    except Exception as e:
        print(f"Error searching {symbol}: {e}")
    return None

def main():
    print("================================================================================")
    print("🔍 INVESTIGASI DATA PEMENANG VS PECUNDANG (DEXSCREENER DATA)")
    print("================================================================================")
    
    print("\n--- WINNERS (RUNNER) ---")
    print(f"{'SYMBOL':<10} | {'LIQ':<10} | {'VOL 24H':<10} | {'SOCIALS':<7} | {'INITIAL LIQ?':<12}")
    
    for sym in winners:
        data = search_dexscreener(sym)
        if data:
            liq = float(data.get("liquidity", {}).get("usd", 0) or 0)
            vol = float(data.get("volume", {}).get("h24", 0) or 0)
            info = data.get("info", {})
            has_social = bool(info.get("websites") or info.get("socials"))
            print(f"{sym:<10} | ${liq:<9.0f} | ${vol:<9.0f} | {str(has_social):<7} | ?")
        else:
            print(f"{sym:<10} | NOT FOUND")
        time.sleep(1) # Rate limit protection

    print("\n--- LOSERS (DUMPED) ---")
    for sym in losers:
        data = search_dexscreener(sym)
        if data:
            liq = float(data.get("liquidity", {}).get("usd", 0) or 0)
            vol = float(data.get("volume", {}).get("h24", 0) or 0)
            info = data.get("info", {})
            has_social = bool(info.get("websites") or info.get("socials"))
            print(f"{sym:<10} | ${liq:<9.0f} | ${vol:<9.0f} | {str(has_social):<7} | ?")
        else:
            print(f"{sym:<10} | NOT FOUND")
        time.sleep(1)

if __name__ == "__main__":
    main()
