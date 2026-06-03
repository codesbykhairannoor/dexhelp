import requests
import time
import sys
import threading

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def fetch_tokens_from_url(url):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return []

def analyze_token(pair):
    created = pair.get("pairCreatedAt", 0)
    if not created: return None
    age_min = (time.time() * 1000 - created) / 60000
    
    # We want to see how much it moved recently
    p5m = float(pair.get("priceChange", {}).get("m5", 0) or 0)
    p1h = float(pair.get("priceChange", {}).get("h1", 0) or 0)
    
    # We'll use price change as a proxy for success. 
    # Real backtest would need OHLCV, but we can't fetch OHLCV for 100 tokens fast enough.
    # Actually, we can fetch OHLCV from Birdeye for a few tokens, or we can just use DexScreener's recent price changes as a rough proxy.
    
    # A true backtest needs to look at the token's trajectory.
    return {
        "symbol": pair.get("baseToken", {}).get("symbol", "UNKNOWN"),
        "age_min": age_min,
        "p5m": p5m,
        "p1h": p1h,
        "liq": float(pair.get("liquidity", {}).get("usd", 0) or 0)
    }

def main():
    print("================================================================================")
    print("🚀 SUPER BACKTEST: ZERO-MINUTE SNIPES vs OLD BAGS")
    print("================================================================================")
    print("Mengumpulkan 100 Token secara acak dari Solana...")
    
    urls = [
        "https://api.dexscreener.com/token-profiles/latest/v1",
        "https://api.dexscreener.com/token-boosts/top/v1",
        # We need search queries to find fresh tokens
        "https://api.dexscreener.com/latest/dex/search?q=pump",
        "https://api.dexscreener.com/latest/dex/search?q=sol",
        "https://api.dexscreener.com/latest/dex/search?q=doge",
        "https://api.dexscreener.com/latest/dex/search?q=cat"
    ]
    
    pairs = []
    for u in urls:
        data = fetch_tokens_from_url(u)
        if isinstance(data, list):
            # token-profiles format
            for d in data:
                if d.get("chainId") == "solana":
                    # We need to fetch pair details
                    p_url = f"https://api.dexscreener.com/latest/dex/tokens/{d.get('tokenAddress')}"
                    p_data = fetch_tokens_from_url(p_url)
                    if p_data and isinstance(p_data, dict) and p_data.get("pairs"):
                        pairs.append(p_data["pairs"][0])
                time.sleep(0.5)
        elif isinstance(data, dict) and data.get("pairs"):
            pairs.extend(data["pairs"])
            
    print(f"Berhasil mengumpulkan {len(pairs)} pasangan trading.")
    
    old_tokens = []
    new_tokens = []
    
    for p in pairs:
        res = analyze_token(p)
        if not res: continue
        if res["liq"] < 5000: continue # Filter micro liq
        
        if res["age_min"] > 60:
            old_tokens.append(res)
        else:
            new_tokens.append(res)
            
    print(f"\nDitemukan: {len(new_tokens)} Koin Baru (< 1 Jam) | {len(old_tokens)} Koin Tua (> 1 Jam)")
    
    # Evaluate Win Rate Proxy (Price change 1h > +30% is a win, < -15% is a loss)
    def evaluate(group, name):
        wins = 0
        losses = 0
        for t in group:
            if t["p1h"] >= 30:
                wins += 1
            elif t["p1h"] <= -15:
                losses += 1
                
        total = wins + losses
        wr = (wins / total * 100) if total > 0 else 0
        print(f"\n--- HASIL: {name} ---")
        print(f"Total Dievaluasi : {total}")
        print(f"Koin Meroket     : {wins}")
        print(f"Koin Hancur      : {losses}")
        print(f"WIN RATE PROXY   : {wr:.1f}%")
        
    evaluate(new_tokens, "KOIN BAYI (ZERO-MINUTE SNIPES)")
    evaluate(old_tokens, "KOIN TUA (MATURE/DISTRIBUTION)")

if __name__ == "__main__":
    main()
