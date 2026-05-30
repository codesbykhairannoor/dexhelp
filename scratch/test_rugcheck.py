import requests
import json

mint = "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm"  # WIF
url = f"https://api.rugcheck.xyz/v1/tokens/{mint}/report"
try:
    r = requests.get(url, timeout=10)
    print("Status Code:", r.status_code)
    if r.status_code == 200:
        data = r.json()
        # Save to file to inspect
        with open("scratch_rugcheck_response.json", "w") as f:
            json.dump(data, f, indent=2)
        print("Success! Saved to scratch_rugcheck_response.json")
        # Print high level keys
        print("Keys:", list(data.keys()))
        print("Risks count:", len(data.get("risks", [])))
        if data.get("risks"):
            print("First risk sample:", data["risks"][0])
    else:
        print("Failed:", r.text[:200])
except Exception as e:
    print("Error:", e)
