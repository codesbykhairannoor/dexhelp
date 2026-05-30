import requests
import json

mints = {
    "noop": "NUpWt8bg4Y63qg62Pe4yWwQQNfxrQ6LLK4uNTrkpump",
    "Shizuku": "BYqcJEf2gTjZv17j95mfgSbN1jVNPow61HUwSwF9pump"
}

for name, mint in mints.items():
    print("\n" + "="*80)
    print(f"DIAGNOSING RUGCHECK DETAILS FOR {name} ({mint})")
    print("="*80)
    url = f"https://api.rugcheck.xyz/v1/tokens/{mint}/report"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            print("Score:", data.get("score"))
            print("Risk Level:", data.get("riskLevel"))
            print("Risks:", data.get("risks"))
            
            # Print markets
            markets = data.get("markets", [])
            print(f"Markets count: {len(markets)}")
            for idx, m in enumerate(markets):
                lp = m.get("lp", {})
                print(f"  Market #{idx+1} ({m.get('marketType')}):")
                print(f"    lpLockedPct: {lp.get('lpLockedPct')}%")
                print(f"    lpUnlocked: {lp.get('lpUnlocked')}")
                print(f"    lpLockedUSD: {lp.get('lpLockedUSD')}")
                print(f"    quoteUSD: {lp.get('quoteUSD')}")
                print(f"    baseUSD: {lp.get('baseUSD')}")
            
            # Print top holders
            holders = data.get("topHolders", [])
            print(f"Top holders count: {len(holders)}")
            insider_pct = sum(float(h.get("pct", 0) or 0) for h in holders if h.get("insider") is True)
            print(f"  Insider Pct: {insider_pct:.1f}%")
            for h in holders[:3]:
                print(f"    Address: {h.get('address')[:8]}... | pct: {h.get('pct'):.2f}% | insider: {h.get('insider')}")
        else:
            print("Failed to fetch:", r.status_code)
    except Exception as e:
        print("Error:", e)
