import os
import sys

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from dex_hunter import _fetch_candidates

print("Testing dynamic token age fetch...")
candidates = _fetch_candidates()
if candidates:
    print(f"Successfully fetched {len(candidates)} candidates.")
    for c in candidates[:5]:
        print(f"Token: {c['symbol']} | Age (sec): {c['age_estimate_sec']:.1f} | Snipe: {c['zero_minute_snipe']}")
else:
    print("No candidates found (filters might be too strict or API issue).")
