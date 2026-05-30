import sys
import os

# Fix path to load dex_hunter
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(os.path.dirname(CURRENT_DIR), "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from dex_hunter import check_token_security, calculate_gem_score
import requests

def test_token(mint, symbol):
    print("\n" + "="*80)
    print(f"[TEST] TESTING TOKEN: {symbol} ({mint})")
    print("="*80)
    res = check_token_security("solana", mint)
    print("Security Status :", res["status"])
    print("Security Flags  :", res["flags"])
    print("Score Impact    :", res["score_impact"])
    
    # Mock pair data for scoring
    pair_data = {
        "address": mint,
        "symbol": symbol,
        "name": symbol,
        "volume_5m": 12000,
        "volume_1h": 85000,
        "volume_24h": 320000,
        "liquidity": 15000,
        "market_cap": 60000,
        "fdv": 60000,
        "price_change_5m": 12.0,
        "price_change_1h": 35.0,
        "txns": {"m5": {"buys": 45, "sells": 10}},
        "info": {"websites": [], "socials": []},
        "boost_amount": 0,
        "boosts_active": 0,
        "age_estimate_sec": 60,
        "zero_minute_snipe": True,
        "has_paid_order": False
    }
    score = calculate_gem_score(pair_data, res)
    print("Calculated Score:", score)

if __name__ == "__main__":
    # 1. Test WIF (Establishment token)
    test_token("EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm", "WIF")
    
    # 2. Test 3 fresh tokens from RugCheck to see the new audits in the wild
    try:
        r = requests.get('https://api.rugcheck.xyz/v1/stats/new_tokens', timeout=5)
        if r.status_code == 200:
            tokens = r.json()[:3]
            print(f"\nFetched {len(tokens)} fresh tokens from RugCheck stats.")
            for t in tokens:
                mint = t.get('mint')
                symbol = t.get('symbol', 'UNKNOWN')
                if mint:
                    test_token(mint, symbol)
        else:
            print("Failed to fetch new tokens:", r.status_code)
    except Exception as e:
        print("Error fetching new tokens:", e)
