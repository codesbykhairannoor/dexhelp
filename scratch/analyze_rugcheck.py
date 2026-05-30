import json

with open("scratch_rugcheck_response.json", "r") as f:
    data = json.load(f)

# Inspect insider and network properties
print("--- INSIDER AND NETWORK DETECTIONS ---")
print("graphInsidersDetected:", data.get("graphInsidersDetected"))
print("insiderNetworks:", data.get("insiderNetworks"))
print("creatorBalance:", data.get("creatorBalance"))
print("creatorTokens:", data.get("creatorTokens"))

print("\n--- LP AND MARKETS ---")
markets = data.get("markets", [])
print(f"Number of markets: {len(markets)}")
for idx, m in enumerate(markets):
    lp = m.get("lp", {})
    print(f"Market #{idx+1} ({m.get('marketType')}):")
    print(f"  lpLockedUSD: {lp.get('lpLockedUSD')}")
    print(f"  lpLockedPct: {lp.get('lpLockedPct')}%")
    print(f"  lpUnlocked: {lp.get('lpUnlocked')}")

print("\n--- VERIFICATION ---")
print("verification:", data.get("verification"))
