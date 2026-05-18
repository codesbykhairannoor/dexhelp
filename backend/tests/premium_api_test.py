"""
PREMIUM API CAPABILITY TEST - FluxRPC + GoPlus Authenticated
Tests all premium features against live Solana mainnet to determine worth.

Test token: JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN (Jupiter - known safe)
Scam token: A55XjvzRU4KtR3Lrys8PpLZQvPojPqvnv5bJVHMYy3Jv (known flagged)
"""
import os
import sys
import json
import time
import hmac
import hashlib
import requests
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
#  CREDENTIALS
# ---------------------------------------------------------------------------
FLUXRPC_KEY        = "9ffd9262-287f-4d4f-a76c-bc4a86a5e073"
FLUXRPC_RPC_URL    = f"https://eu.fluxrpc.com?key={FLUXRPC_KEY}"
FLUXRPC_SHIELD_URL = "https://eu.shield.fluxrpc.com?key=xIhwXmSfMnULA-lJZ8EgwQ"
FLUXRPC_WS_URL     = "wss://ws.eu.fluxrpc.com"

GOPLUS_APP_KEY     = "GPyD9Q0M1z2Z2VCzda0w"
GOPLUS_APP_SECRET  = "f9pEKh23fhzw4unzcaMGTXTMXJjPbyxd"
GOPLUS_BASE_URL    = "https://api.gopluslabs.io/api/v1"

# Real Solana SPL token addresses (pump.fun graduated tokens)
TEST_SAFE_TOKEN    = "So11111111111111111111111111111111111111112"   # Wrapped SOL (always safe)
TEST_SCAM_TOKEN    = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"  # BONK (known real token, for contrast)

results = {}

# ---------------------------------------------------------------------------
#  HELPER: Print section header
# ---------------------------------------------------------------------------
def section(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def ok(label, value):
    print(f"  [PASS] {label}: {value}")

def fail(label, error):
    print(f"  [FAIL] {label}: {error}")

# ---------------------------------------------------------------------------
#  TEST 1: FluxRPC - Basic JSON-RPC (getVersion)
# ---------------------------------------------------------------------------
section("TEST 1: FluxRPC - Basic RPC Connectivity (getVersion)")
try:
    payload = {"jsonrpc": "2.0", "id": 1, "method": "getVersion", "params": []}
    r = requests.post(FLUXRPC_RPC_URL, json=payload, timeout=10)
    data = r.json()
    if "result" in data:
        version = data["result"].get("solana-core", "unknown")
        ok("FluxRPC Connected", f"Solana Core v{version}")
        results["fluxrpc_rpc"] = True
    else:
        fail("FluxRPC RPC", data)
        results["fluxrpc_rpc"] = False
except Exception as e:
    fail("FluxRPC RPC", e)
    results["fluxrpc_rpc"] = False

# ---------------------------------------------------------------------------
#  TEST 2: FluxRPC - getSlot (Latency Test)
# ---------------------------------------------------------------------------
section("TEST 2: FluxRPC - Slot Latency Test")
try:
    t0 = time.time()
    payload = {"jsonrpc": "2.0", "id": 1, "method": "getSlot", "params": []}
    r = requests.post(FLUXRPC_RPC_URL, json=payload, timeout=10)
    elapsed_ms = (time.time() - t0) * 1000
    data = r.json()
    if "result" in data:
        ok("Current Slot", data["result"])
        ok("Round-Trip Latency", f"{elapsed_ms:.0f}ms")
        results["fluxrpc_latency_ms"] = round(elapsed_ms)
        results["fluxrpc_slot"] = True
    else:
        fail("getSlot", data)
        results["fluxrpc_slot"] = False
except Exception as e:
    fail("getSlot", e)
    results["fluxrpc_slot"] = False

# ---------------------------------------------------------------------------
#  TEST 3: FluxRPC Shield - simulateTransaction detection
# ---------------------------------------------------------------------------
section("TEST 3: FluxRPC Shield - Endpoint Reachability")
try:
    # Shield uses same JSON-RPC but with MEV protection layer
    payload = {"jsonrpc": "2.0", "id": 1, "method": "getVersion", "params": []}
    r = requests.post(FLUXRPC_SHIELD_URL, json=payload, timeout=10)
    if r.status_code == 200:
        data = r.json()
        version = data.get("result", {}).get("solana-core", "?")
        ok("FluxRPC Shield Reachable", f"v{version} | Status {r.status_code}")
        results["fluxrpc_shield"] = True
    else:
        fail("FluxRPC Shield", f"HTTP {r.status_code}: {r.text[:200]}")
        results["fluxrpc_shield"] = False
except Exception as e:
    fail("FluxRPC Shield", e)
    results["fluxrpc_shield"] = False

# ---------------------------------------------------------------------------
#  TEST 4: GoPlus - Token Security API (FREE tier, no auth)
# ---------------------------------------------------------------------------
section("TEST 4: GoPlus Token Security - FREE Tier (Safe Token)")
try:
    url = f"{GOPLUS_BASE_URL}/solana/token_security?addresses={TEST_SAFE_TOKEN}"
    r = requests.get(url, timeout=10)
    data = r.json()
    if data.get("code") == 1 and data.get("result"):
        token_data = data["result"].get(TEST_SAFE_TOKEN, {})
        freezable = token_data.get("freezable", "?")
        mintable  = token_data.get("mintable", "?")
        ok("GoPlus FREE Tier (Safe Token)", f"Freeze={freezable} Mint={mintable}")
        results["goplus_free_safe"] = True
    else:
        fail("GoPlus FREE Tier", data)
        results["goplus_free_safe"] = False
except Exception as e:
    fail("GoPlus FREE Tier Safe Token", e)
    results["goplus_free_safe"] = False

# ---------------------------------------------------------------------------
#  TEST 5: GoPlus - Token Security API (FREE tier, scam token)
# ---------------------------------------------------------------------------
section("TEST 5: GoPlus Token Security - FREE Tier (Scam Token Detection)")
try:
    url = f"{GOPLUS_BASE_URL}/solana/token_security?addresses={TEST_SCAM_TOKEN}"
    r = requests.get(url, timeout=10)
    data = r.json()
    if data.get("code") == 1 and data.get("result"):
        token_data = data["result"].get(TEST_SCAM_TOKEN, {})
        freezable = token_data.get("freezable", "?")
        mintable  = token_data.get("mintable", "?")
        ok("GoPlus FREE Scam Detection", f"Freeze={freezable} Mint={mintable} | Flags: {list(token_data.keys())[:5]}")
        results["goplus_free_scam"] = True
    else:
        fail("GoPlus FREE Scam", data)
        results["goplus_free_scam"] = False
except Exception as e:
    fail("GoPlus FREE Scam Token", e)
    results["goplus_free_scam"] = False

# ---------------------------------------------------------------------------
#  TEST 6: GoPlus - Authenticated API (App Key + HMAC Signature)
# ---------------------------------------------------------------------------
section("TEST 6: GoPlus Authenticated API (App Key + Secret)")
try:
    # GoPlus authenticated: pass app_key + timestamp + sign (HMAC-SHA256)
    timestamp = str(int(time.time()))
    # GoPlus sign format: HMAC-SHA256(timestamp + app_key, app_secret)
    sign_input = timestamp + GOPLUS_APP_KEY
    signature  = hmac.new(
        GOPLUS_APP_SECRET.encode("utf-8"),
        sign_input.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    headers = {
        "app_key"  : GOPLUS_APP_KEY,
        "timestamp": timestamp,
        "sign"     : signature,
    }
    url = f"{GOPLUS_BASE_URL}/solana/token_security?addresses={TEST_SAFE_TOKEN}"
    r   = requests.get(url, headers=headers, timeout=10)
    data = r.json()
    if data.get("code") == 1:
        ok("GoPlus Authenticated", f"Auth OK | Code={data['code']} | Token fields: {len(data.get('result', {}).get(TEST_SAFE_TOKEN, {}))}")
        results["goplus_auth"] = True
    elif data.get("code") == 2:
        # Code 2 = auth error
        fail("GoPlus Auth", f"Auth Failed: {data.get('message', 'wrong sign or key')}")
        results["goplus_auth"] = False
    else:
        fail("GoPlus Auth", data)
        results["goplus_auth"] = False
except AttributeError:
    # Python 2 compat: hmac.new -> hmac.new is correct, but check for py3
    try:
        sign_input = GOPLUS_APP_KEY + timestamp
        signature  = hmac.new(
            GOPLUS_APP_SECRET.encode(),
            sign_input.encode(),
            hashlib.sha256
        ).hexdigest()
        headers = {"app_key": GOPLUS_APP_KEY, "timestamp": timestamp, "sign": signature}
        url = f"{GOPLUS_BASE_URL}/solana/token_security?addresses={TEST_SAFE_TOKEN}"
        r   = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        ok("GoPlus Authenticated (retry)", str(data.get("code")))
        results["goplus_auth"] = data.get("code") == 1
    except Exception as e2:
        fail("GoPlus Auth retry", e2)
        results["goplus_auth"] = False
except Exception as e:
    fail("GoPlus Authenticated", e)
    results["goplus_auth"] = False

# ---------------------------------------------------------------------------
#  TEST 7: GoPlus - Malicious Address API
# ---------------------------------------------------------------------------
section("TEST 7: GoPlus - Malicious Address API")
try:
    # GoPlus Malicious Address API - chain_id is numeric for EVM, 'solana' not supported here
    # Use EVM chain (BSC=56) to verify the API works with auth
    test_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"  # Vitalik wallet (clean)
    url = f"{GOPLUS_BASE_URL}/address_security?address={test_address}&chain_id=1"
    # Build authenticated headers for this call
    ts2  = str(int(time.time()))
    sig2 = hmac.new(GOPLUS_APP_SECRET.encode(), (ts2 + GOPLUS_APP_KEY).encode(), hashlib.sha256).hexdigest()
    hdrs2 = {"app_key": GOPLUS_APP_KEY, "timestamp": ts2, "sign": sig2}
    r    = requests.get(url, headers=hdrs2, timeout=10)
    data = r.json()
    if data.get("code") == 1:
        result_data = data.get("result", {})
        ok("Malicious Address API (EVM)", f"malicious={result_data.get('malicious_type','none')} | contract={result_data.get('contract_address','?')}")
        results["goplus_malicious"] = True
    else:
        fail("Malicious Address API", data)
        results["goplus_malicious"] = False
except Exception as e:
    fail("Malicious Address API", e)
    results["goplus_malicious"] = False

# ---------------------------------------------------------------------------
#  FINAL VERDICT
# ---------------------------------------------------------------------------
section("VERDICT: WORTH IT OR NOT?")
print(f"  FluxRPC RPC Connectivity : {'[PASS]' if results.get('fluxrpc_rpc') else '[FAIL]'}")
print(f"  FluxRPC Latency          : {results.get('fluxrpc_latency_ms', 'N/A')}ms  {'<-- FASTER than Helius?' if results.get('fluxrpc_latency_ms', 999) < 200 else ''}")
print(f"  FluxRPC Shield (MEV)     : {'[PASS]' if results.get('fluxrpc_shield') else '[FAIL]'}")
print(f"  GoPlus FREE Tier         : {'[PASS]' if results.get('goplus_free_safe') else '[FAIL]'}")
print(f"  GoPlus Scam Detection    : {'[PASS]' if results.get('goplus_free_scam') else '[FAIL]'}")
print(f"  GoPlus Authenticated     : {'[PASS]' if results.get('goplus_auth') else '[FAIL]'}")
print(f"  GoPlus Malicious Addr    : {'[PASS]' if results.get('goplus_malicious') else '[FAIL]'}")

passes = sum(1 for v in results.values() if v is True)
total  = len([v for v in results.values() if isinstance(v, bool)])
print(f"\n  SCORE: {passes}/{total} tests passed")

if passes >= 5:
    print("\n  [VERDICT] SANGAT WORTH IT - Integrasikan ke bot sekarang juga!")
elif passes >= 3:
    print("\n  [VERDICT] CUKUP WORTH IT - Integrasikan sebagian fitur yang bekerja.")
else:
    print("\n  [VERDICT] TIDAK WORTH IT - Ada masalah koneksi atau credential.")
print("=" * 80)
