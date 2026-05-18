import requests, time, hmac, hashlib

GOPLUS_APP_KEY    = "GPyD9Q0M1z2Z2VCzda0w"
GOPLUS_APP_SECRET = "f9pEKh23fhzw4unzcaMGTXTMXJjPbyxd"
HELIUS_URL        = "https://mainnet.helius-rpc.com/?api-key=bff8981d-d1fd-450b-9cd1-81344c455006"
FLUXRPC_URL       = "https://eu.fluxrpc.com?key=9ffd9262-287f-4d4f-a76c-bc4a86a5e073"

print("=" * 60)
print("DEEP DIAGNOSTIC: GoPlus Solana + Latency Benchmark")
print("=" * 60)

# 1. GoPlus Solana token_security - try 3 known tokens
addrs = [
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E",
]
print("\n[GoPlus Solana Token Security - FREE]")
for addr in addrs:
    try:
        r = requests.get(
            "https://api.gopluslabs.io/api/v1/solana/token_security",
            params={"addresses": addr},
            timeout=8
        )
        d = r.json()
        code = d.get("code")
        msg  = d.get("message", "ok")
        keys = list(d.get("result", {}).get(addr, {}).keys())[:4] if d.get("result") else []
        print("  addr=" + addr[:12] + "... code=" + str(code) + " msg=" + str(msg) + " keys=" + str(keys))
    except Exception as e:
        print("  ERROR: " + str(e))

# 2. Latency comparison: Helius vs FluxRPC
print("\n[RPC Latency Comparison - 3 rounds each]")
helius_times = []
flux_times   = []
payload = {"jsonrpc": "2.0", "id": 1, "method": "getSlot", "params": []}

for i in range(3):
    try:
        t0 = time.time()
        rh = requests.post(HELIUS_URL, json=payload, timeout=10)
        helius_times.append((time.time() - t0) * 1000)
    except Exception as e:
        helius_times.append(9999)

    try:
        t0 = time.time()
        rf = requests.post(FLUXRPC_URL, json=payload, timeout=10)
        flux_times.append((time.time() - t0) * 1000)
    except Exception as e:
        flux_times.append(9999)

avg_helius = sum(helius_times) / len(helius_times)
avg_flux   = sum(flux_times)   / len(flux_times)
print("  Helius avg  : " + str(round(avg_helius)) + "ms | rounds: " + str([round(x) for x in helius_times]))
print("  FluxRPC avg : " + str(round(avg_flux))   + "ms | rounds: " + str([round(x) for x in flux_times]))

if avg_helius < avg_flux:
    diff = avg_flux - avg_helius
    print("  VERDICT: Helius LEBIH CEPAT (selisih " + str(round(diff)) + "ms) - FluxRPC tidak worth it untuk RPC!")
else:
    diff = avg_helius - avg_flux
    print("  VERDICT: FluxRPC LEBIH CEPAT (selisih " + str(round(diff)) + "ms) - Worth it upgrade RPC!")

# 3. GoPlus HMAC debug
print("\n[GoPlus Authenticated - HMAC Debug]")
ts   = str(int(time.time()))
msg  = ts + GOPLUS_APP_KEY
sig  = hmac.new(GOPLUS_APP_SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()
print("  timestamp  : " + ts)
print("  sign_input : " + msg[:30] + "...")
print("  signature  : " + sig[:30] + "...")

headers = {
    "app_key"  : GOPLUS_APP_KEY,
    "timestamp": ts,
    "sign"     : sig,
    "accept"   : "application/json"
}
try:
    r2 = requests.get(
        "https://api.gopluslabs.io/api/v1/solana/token_security",
        params={"addresses": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"},
        headers=headers,
        timeout=8
    )
    d2 = r2.json()
    print("  Auth code  : " + str(d2.get("code")) + " | msg: " + str(d2.get("message", "ok")))
    if d2.get("code") == 1 and d2.get("result"):
        print("  AUTH SUCCESS - Premium tier active!")
    elif d2.get("code") == 4012:
        print("  AUTH FAILED - Signature format wrong, GoPlus may need different HMAC format")
    else:
        print("  Response   : " + str(d2)[:200])
except Exception as e:
    print("  ERROR: " + str(e))

print("\n" + "=" * 60)
