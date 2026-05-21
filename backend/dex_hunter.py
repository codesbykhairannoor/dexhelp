import os
import json
import websocket
import requests
import time
import threading
from collections import defaultdict
from dotenv import load_dotenv

# Load env vars explicitly
load_dotenv()

# ============================================================================-
#  CONFIG & INITIALIZATION
# ============================================================================-
SCAN_INTERVAL_SEC     = 60     # Scan DexScreener every 1 minute
MIN_LIQUIDITY_USD     = 25000  # Minimum $25k liquidity for safety (Up from $10k to filter cheap scams)
MIN_MCAP_USD          = 35000  # Minimum $35k marketcap to filter dust (Up from $15k)
MAX_MCAP_USD          = 10000000 # Max $10M to target early stage gems
DEX_CHAINS            = ["solana", "base"] # Top high-yield meme networks

CHAIN_MAPPING = {
    "solana": "solana",
    "base": "8453",
    "ethereum": "1",
    "bsc": "56"
}

_scanned_gems = []
_verified_profiles = set()
_trending_metas = []
_boost_tracker = {}
_community_takeover_tokens = set()  # NEW: Community Takeover signal
_scan_lock = threading.Lock()
_scan_thread = None
_is_running = False

# ============================================================================-
#  DOUBLE-SAFETY AUDIT STACK (GoPlus + Honeypot.is + RugCheck.xyz)
# ============================================================================-

def check_token_security(chain: str, address: str) -> dict:
    """
    ScamShield Engine: Double-Safety Audit Stack.
    Combines GoPlus Security, Honeypot.is, and RugCheck.xyz APIs:
    - EVM (Base/ETH/BSC): GoPlus + Honeypot.is simulation (actual buy/sell taxes)
    - Solana: GoPlus + RugCheck.xyz Report fallback
    """
    goplus_chain = CHAIN_MAPPING.get(chain.lower())
    if not goplus_chain:
        return {"status": "UNSUPPORTED", "score_impact": 0, "flags": ["Unsupported Network"]}

    flags = []
    is_safe = True
    score_impact = 0

    # ------------------------------------------------------------------------
    #  SOLANA SECURITY STACK (RugCheck.xyz + GoPlus Fallback)
    # ------------------------------------------------------------------------
    if chain.lower() == "solana":
        # Lapis 1: RugCheck.xyz Report API
        rugcheck_ok = False
        try:
            rug_url = f"https://api.rugcheck.xyz/v1/tokens/{address}/report"
            r = requests.get(rug_url, timeout=5)
            if r.status_code == 200:
                rugcheck_ok = True
                data = r.json()
                score = data.get("score", 0)
                risk_level = data.get("riskLevel", "Good")
                
                # Check RugCheck score thresholds (Strict limit lowered from 1500 to 600)
                if score > 600 or risk_level in ["Danger", "Rugged"]:
                    flags.append(f"RUGCHECK_DANGER (Score:{score})")
                    is_safe = False
                elif score > 250:
                    flags.append(f"RUGCHECK_WARNING (Score:{score})")
                    score_impact -= 10
                
                # Extract specific risk flags from RugCheck (Block unlocked LP & mutable metadata)
                for risk in data.get("risks", []):
                    risk_name = str(risk.get("name", "")).lower()
                    risk_level = risk.get("level", "")
                    
                    # Mark unsafe if LP is unlocked, single holder owns LP, metadata is mutable, or explicitly danger
                    if risk_level == "danger" or any(x in risk_name for x in ["unlocked", "mutable", "single holder", "mintable"]):
                        flags.append(f"RC_{risk.get('name', '').upper().replace(' ', '_')}")
                        is_safe = False
            else:
                flags.append(f"RUGCHECK_API_ERROR_STATUS_{r.status_code}")
                is_safe = False
        except Exception as e:
            flags.append(f"RUGCHECK_TIMEOUT_FAILED_{type(e).__name__}")
            is_safe = False

        # Lapis 2: GoPlus Solana API
        try:
            url = f"https://api.gopluslabs.io/api/v1/solana/token_security?addresses={address}"
            res = requests.get(url, timeout=5).json()
            if res.get("code") == 1 and res.get("result"):
                data = res["result"].get(address, {})
                
                # Freezable authority (ultimate Solana rug)
                if str(data.get("freezable", "0")) == "1":
                    flags.append("FREEZABLE_ENABLED")
                    is_safe = False
                
                # Mintable check (dev infinite printing)
                if str(data.get("mintable", "0")) == "1":
                    flags.append("MINTABLE_ENABLED")
                    is_safe = False
                    
                # Concentration check
                top10_share = float(data.get("top10_holders_share", 0)) * 100
                if top10_share > 60:
                    flags.append(f"WHALE_CONCENTRATION ({top10_share:.0f}%)")
                    score_impact -= 15
        except Exception:
            pass

        # Lapis 3: RugCheck Holder Concentration (NEW: Top-1 Holder Anti-Whale Check)
        try:
            holders_url = f"https://api.rugcheck.xyz/v1/tokens/{address}/holders"
            rh = requests.get(holders_url, timeout=5)
            if rh.status_code == 200:
                holders = rh.json()
                if isinstance(holders, list) and holders:
                    top1_pct = float(holders[0].get("pct", 0)) * 100
                    if top1_pct > 20:
                        flags.append(f"WHALE_TOP1_HOLDER ({top1_pct:.1f}%)")
                        is_safe = False
                    elif top1_pct < 5:
                        score_impact += 10  # Healthy distributed ownership
        except Exception:
            pass

        # Lapis 4: Solscan Pro API V2.0 Audit (Premium Forensic Fallback)
        solscan_api_key = os.getenv("SOLSCAN_API_KEY")
        if solscan_api_key:
            try:
                solscan_url = f"https://pro-api.solscan.io/v2.0/token/meta?address={address}"
                s_headers = {"token": solscan_api_key, "Accept": "application/json"}
                sr = requests.get(solscan_url, headers=s_headers, timeout=5)
                if sr.status_code == 200:
                    sdata = sr.json()
                    if sdata.get("success") is True and sdata.get("data"):
                        t_meta = sdata["data"]
                        mint_auth = t_meta.get("mint_authority")
                        freeze_auth = t_meta.get("freeze_authority")
                        
                        # Block if mint or freeze authority is active (not null/empty)
                        if mint_auth is not None and mint_auth != "":
                            flags.append("SOLSCAN_MINTABLE_DANGER")
                            is_safe = False
                        if freeze_auth is not None and freeze_auth != "":
                            flags.append("SOLSCAN_FREEZABLE_DANGER")
                            is_safe = False
            except Exception:
                pass

    # ------------------------------------------------------------------------
    #  EVM SECURITY STACK (Honeypot.is + GoPlus Security)
    # ------------------------------------------------------------------------
    else:
        # Lapis 1: Honeypot.is API (Simulation Execution)
        try:
            hp_url = f"https://api.honeypot.is/v2/IsHoneypot?address={address}"
            r = requests.get(hp_url, timeout=5)
            if r.status_code == 200:
                data = r.json()
                hp_res = data.get("honeypotResult", {})
                sim_res = data.get("simulationResult", {})
                
                if hp_res.get("isHoneypot") is True:
                    flags.append("HONEYPOT_SCAM")
                    is_safe = False
                
                buy_tax = float(sim_res.get("buyTax", 0))
                sell_tax = float(sim_res.get("sellTax", 0))
                if buy_tax > 10 or sell_tax > 10:
                    flags.append(f"HIGH_TAX (Buy:{buy_tax:.0f}% Sell:{sell_tax:.0f}%)")
                    score_impact -= 10
        except Exception:
            pass

        # Lapis 2: GoPlus Security API
        try:
            url = f"https://api.gopluslabs.io/api/v1/token_security/{goplus_chain}?addresses={address}"
            res = requests.get(url, timeout=5).json()
            if res.get("code") == 1 and res.get("result"):
                data = res["result"].get(address, {})
                
                # Honeypot double safety
                if str(data.get("is_honeypot", "0")) == "1" or str(data.get("cannot_sell", "0")) == "1":
                    flags.append("HONEYPOT_DOUBLE_FLAG")
                    is_safe = False
                
                # Mint function
                if str(data.get("is_mintable", "0")) == "1":
                    flags.append("MINTABLE_CONTRACT")
                    score_impact -= 15
                    
                # Pausable contract
                if str(data.get("transfer_pausable", "0")) == "1":
                    flags.append("PAUSABLE_CONTRACT")
                    is_safe = False
        except Exception:
            pass

    # ------------------------------------------------------------------------
    #  FINAL EVALUATION
    # ------------------------------------------------------------------------
    # Deduplicate flags list
    flags = list(set(flags))
    
    if is_safe and not flags:
        status = "CLEAN & SAFE"
        score_impact += 25
    elif is_safe:
        status = "WARNINGS"
        score_impact += 5
    else:
        status = "DANGEROUS SCAM"
        score_impact -= 40

    return {
        "status": status,
        "flags": flags if flags else ["None"],
        "score_impact": score_impact
    }

# ============================================================================-
#  PREDATOR SCORING ENGINE
# ============================================================================-

def calculate_gem_score(pair_data: dict, security: dict) -> int:
    """
    Ranks newly launched or trending pairs on a scale of 0 to 100.
    Integrates safety, growth velocity, liquidity health, and social presence.
    V10.0: Added 6 new API signals: token age window, volume acceleration,
    active boosts, community takeover, FDV inflation ratio, top-1 holder check.
    """
    score = 50 # Base intermediate score
    
    # 1. Security Impact (GoPlus + RugCheck + Honeypot.is)
    score += security.get("score_impact", 0)
    if security.get("status") == "DANGEROUS SCAM":
        return max(5, score) # Cap scam tokens to minimal score

    # V16.0 ZERO-MINUTE SNIPE BONUS
    if pair_data.get("zero_minute_snipe"):
        score += 40  # Balanced boost for snipes that pass strict pre-filters

    # NEW SIGNAL 1: Token Age Window (Optimal Entry Timing)
    # Too young = developer can still rug. Too old = pump already over.
    age_sec = pair_data.get("age_estimate_sec", 3600)
    if pair_data.get("zero_minute_snipe"):
        # Zero-minute snipes bypass the young age penalty because they undergo strict social & volume checks
        pass
    elif 300 <= age_sec <= 10800:   # Sweet spot: 5 min - 3 hours (early entry allowed since security is mandatory)
        score += 20
    elif age_sec < 300:           # < 5 minutes: dangerously early
        score -= 40
    elif age_sec > 43200:         # > 12 hours: momentum likely exhausted
        score -= 20

    # NEW SIGNAL 2: Volume Acceleration (Is momentum GROWING right now?)
    # Compare h1 volume vs the average hourly volume from h24 baseline
    vol_1h = float(pair_data.get("volume_1h", 0) or 0)
    vol_24h = float(pair_data.get("volume_24h", 0) or 0)
    if vol_24h > 0:
        baseline_hourly = vol_24h / 24.0
        vol_accel = vol_1h / baseline_hourly if baseline_hourly > 0 else 1.0
        if vol_accel > 3.0:
            score += 15  # Volume 3x baseline = momentum explosion!
        elif vol_accel > 1.5:
            score += 8   # Volume above average = healthy uptrend
        elif vol_accel < 0.5:
            score -= 10  # Volume drying up = trend is dying

    # V15.0 5-Minute Volume Surge check (Micro-breakout sensor)
    vol_5m = float(pair_data.get("volume_5m", 0) or 0)
    avg_5m_vol = vol_1h / 12.0
    vol_surge_5m = vol_5m / avg_5m_vol if avg_5m_vol > 0 else 1.0
    if vol_surge_5m >= 2.5:
        score += 15  # Strong micro volume surge
    elif vol_surge_5m < 0.8:
        score -= 15  # Volume stalling/dry-up

    # NEW SIGNAL 3: Active Boosts (Someone paying RIGHT NOW to promote this)
    active_boosts = pair_data.get("boosts_active", 0)
    if active_boosts > 0:
        score += 15  # Active paid promotion = real hype, not ghost

    # NEW SIGNAL 4: Community Takeover Bonus (Strongest bullish narrative)
    if pair_data.get("address") in _community_takeover_tokens:
        score += 25  # Community took over = massive revival narrative!

    # NEW SIGNAL 5: FDV vs MarketCap Inflation Ratio (Dump risk from unlocked supply)
    fdv = float(pair_data.get("fdv", 0) or 0)
    mcap = float(pair_data.get("market_cap", 0) or 0)
    if fdv > 0 and mcap > 0:
        inflation_ratio = fdv / mcap
        if inflation_ratio > 10:
            score -= 20  # 90%+ supply not yet circulating = massive future dump risk!
        elif inflation_ratio <= 1.2:
            score += 10  # Almost all supply already in circulation = safe!
        
    # 2. Liquidity depth & Mcap ratio (Healthy memecoins: 10% to 35% L/MC ratio)
    liq = float(pair_data.get("liquidity", 0) or 0)
    mcap = float(pair_data.get("market_cap", 0) or pair_data.get("marketCap", 0) or 0)
    if mcap > 0:
        liq_ratio = liq / mcap
        if 0.10 <= liq_ratio <= 0.35: score += 15 # Perfect sweet spot!
        elif liq_ratio >= 0.35: score += 8 # Excess liquidity relative to Mcap
        elif liq_ratio < 0.05: score -= 25 # High slippage risk

    # 3. Buy/Sell Volume Momentum & Exhaustion Guard (5 Minutes)
    tx_5m = pair_data.get("txns", {}).get("m5", {})
    buys = int(tx_5m.get("buys", 0))
    sells = int(tx_5m.get("sells", 0))
    total_tx = buys + sells
    
    if total_tx > 80: score += 15
    elif total_tx > 30: score += 8
    
    p5m = float(pair_data.get("price_change_5m", 0) or 0)
    
    # A. Whale Distribution Guard (Whales exiting on retail buyers)
    # If the count of buys is way higher than sells (FOMO), but the price is dropping -> classic whale distribution trap!
    if sells > 0 and (buys / sells) >= 1.7:
        if p5m < -1.0:
            score -= 15 # "Lelah Naik" Trap! Whales are using retail as exit liquidity.
        else:
            score += 10 # Healthy buying pressure
            
    # B. Price-Volume Exhaustion Guard (Fatigue check)
    # High volume (>15% of liquidity) with flat price action indicates a heavy ceiling block (distribution).
    vol_5m = float(pair_data.get("volume_5m", 0) or 0)
    if liq > 0 and vol_5m > (liq * 0.15) and -2.0 <= p5m <= 2.0:
        score -= 15 # Price is stalling despite heavy volume. Momentum exhausted!

    # 4. DexScreener Profile completeness (Social status)
    info = pair_data.get("info", {})
    has_website = 1 if any("website" in str(w.get("type", "")).lower() for w in info.get("websites", [])) else 0
    has_twitter = 1 if any("twitter" in str(s.get("type", "")).lower() for s in info.get("socials", [])) else 0
    has_telegram = 1 if any("telegram" in str(s.get("type", "")).lower() for s in info.get("socials", [])) else 0
    
    socials_count = has_website + has_twitter + has_telegram
    score += (socials_count * 4) # Real project effort boost

    # 5. DexScreener Paid Profile Listing Bonus (Premium legitimacy Check)
    if pair_data.get("address") in _verified_profiles:
        score += 20 # Massively trust official paid listings!

    # 6. Community Boost Velocity Bonus (Viral Hype Sensor)
    boosts = int(pair_data.get("boost_amount", 0))
    if boosts > 500:
        score += 15 # Explosive momentum
    elif boosts > 100:
        score += 8  # High community participation

    # 7. FOMO Shield & Entry Timing Optimizer (Optimal Entry Point Check)
    p5m = float(pair_data.get("price_change_5m", 0) or 0)
    p1h = float(pair_data.get("price_change_1h", 0) or 0)
    
    # A. FOMO Shield: Anti-Overbought / Anti-Top Buying (V15.0 strict limit)
    # Reject entry if 5m price change > 45% or 1h price change > 150%
    if p5m > 45.0 or p1h > 150.0:
        score -= 45 # Highly overbought! Deduct heavily to prevent top-buying
    
    # B. Consolidation Support Finder / Early Momentum (Optimal entry timing)
    elif 5.0 <= p5m <= 40.0 and p1h <= 100.0:
        score += 15 # Healthy early surge / consolidation entry
        
    # C. Severe Dump Protection (Falling knife safety)
    elif p5m < -25.0:
        score -= 30 # Avoid falling knife dump tokens

    # 8. DexScreener Verified Paid Orders Bonus (V6 Premium legitimacy Check)
    if pair_data.get("has_paid_order"):
        score += 20
        
    # 9. Narrative Meta Alignment (V6 trending narrative match)
    if any(meta in pair_data.get("name", "").lower() or meta in pair_data.get("symbol", "").lower() for meta in _trending_metas):
        score += 15

    return max(0, min(100, score))

# ============================================================================-
#  CORE SCANNING PIPELINE
# ============================================================================-

def _fetch_candidates() -> list:
    """V16.5 BIRDEYE ZERO-MINUTE HUNTER: Fetch ultra-fresh tokens from RugCheck and verify on Birdeye"""
    candidates = {}
    
    # 1. Fetch ultra-fresh tokens from RugCheck
    new_tokens = []
    try:
        r = requests.get('https://api.rugcheck.xyz/v1/stats/new_tokens', timeout=5)
        if r.status_code == 200:
            new_tokens = r.json()
    except Exception as e:
        print(f"[DEX HUNTER] Gagal mengambil new_tokens: {e}")
        
    if not new_tokens:
        return []

    # 2. Iterate and check against Birdeye for Volume & Liquidity
    birdeye_key = os.getenv("BIRDEYE_API_KEY", "")
    
    # Scan tokens at index 15 to 20 (roughly 2-3 mins old) so they have time to build $10k+ liquidity and volume
    for t in new_tokens[15:20]:  
        mint = t.get('mint')
        if not mint:
            continue
            
        # Basic pre-filter: Token MUST be safe on chain (no mint/freeze authority)
        mint_auth = t.get('mintAuthority', '')
        freeze_auth = t.get('freezeAuthority', '')
        if (mint_auth != '' and mint_auth is not None) or (freeze_auth != '' and freeze_auth is not None):
            continue  # Scam potential, skip immediately
            
        # Verify if it has liquidity & volume on Birdeye
        try:
            if not birdeye_key:
                print("[DEX HUNTER] BIRDEYE_API_KEY missing in .env!", flush=True)
                break
                
            be_url = f"https://public-api.birdeye.so/defi/token_overview?address={mint}"
            be_headers = {"X-API-KEY": birdeye_key, "Accept": "application/json"}
            be_r = requests.get(be_url, headers=be_headers, timeout=5)
            
            if be_r.status_code == 200:
                be_data = be_r.json().get('data', {})
                if not be_data:
                    continue
                    
                liq = float(be_data.get("liquidity", 0) or 0)
                mcap = float(be_data.get("marketCap", 0) or 0)
                
                # V16.7 BIRDEYE ULTRA-STRICT QUALITY FILTERS FOR PUMP.FUN
                # 1. Require higher minimum liquidity to ensure a solid orderbook base
                if liq >= 10000:
                    # 2. Require Social Presence (serious projects fill out socials, scams don't)
                    extensions = be_data.get("extensions", {}) or {}
                    has_social = bool(extensions.get("twitter") or extensions.get("telegram") or extensions.get("website"))
                    if not has_social:
                        continue
                        
                    # 3. Require High Organic Activity (Filter out single-wallet bundlers and dead pools)
                    unique_wallets_5m = int(be_data.get("uniqueWallet5m", 0) or 0)
                    v5m = float(be_data.get("v5mUSD", 0) or 0)
                    trade5m = int(be_data.get("trade5m", 0) or 0)
                    if unique_wallets_5m < 20 or v5m < 2500 or trade5m < 40:
                        continue

                    # 4. Require strong buying pressure (Smart Money entering)
                    buys = int(be_data.get("buy5m", 0) or 0)
                    sells = int(be_data.get("sell5m", 0) or 0)
                    if buys >= 15 and (buys > (sells * 2) or (buys > 15 and sells == 0)):
                        
                        candidates[mint] = {
                            "chain": "solana",
                            "pair_address": mint, # Birdeye overview is token-centric
                            "symbol": be_data.get("symbol", "UNKNOWN"),
                            "name": be_data.get("name", "UNKNOWN"),
                            "address": mint,
                            "price": float(be_data.get("price", 0) or 0),
                            "volume_5m": v5m,
                            "volume_1h": float(be_data.get("v1hUSD", 0) or 0),
                            "volume_24h": float(be_data.get("v24hUSD", 0) or 0),
                            "liquidity": liq,
                            "market_cap": mcap,
                            "fdv": float(be_data.get("fdv", 0) or 0),
                            "price_change_5m": float(be_data.get("priceChange5mPercent", 0) or 0),
                            "price_change_1h": float(be_data.get("priceChange1hPercent", 0) or 0),
                            "txns": {"m5": {"buys": buys, "sells": sells}},
                            "info": {"imageUrl": be_data.get("logoURI", "")},
                            "url": f"https://birdeye.so/token/{mint}?chain=solana",
                            "boost_amount": 0, 
                            "boosts_active": 0,
                            "age_estimate_sec": 60, # Dummy age to pass downstream filters
                            "zero_minute_snipe": True # Flag for live_paper_trader
                        }
        except Exception as e:
            pass
            
    return list(candidates.values())

def _scan_pipeline():
    """Main background pipeline that fetches, filters, audits, and ranks gems."""
    global _scanned_gems, _is_running
    print("[DEXSCREENER PREDATOR] Background pipeline active.", flush=True)
    
    while _is_running:
        try:
            raw_gems = _fetch_candidates()
            if not raw_gems:
                time.sleep(SCAN_INTERVAL_SEC)
                continue
                
            # Limit processing to top 25 highest-momentum candidates to save resources
            raw_gems.sort(key=lambda x: x.get("volume_5m", 0), reverse=True)
            subset = raw_gems[:25]
            
            processed = []
            for gem in subset:
                # 1. Run live Scam-Shield audit via GoPlus + Honeypot + RugCheck
                security = check_token_security(gem["chain"], gem["address"])
                
                # V6 Upgrade: Verify if developer has approved paid orders
                has_paid_order = False
                try:
                    order_url = f"https://api.dexscreener.com/orders/v1/{gem['chain']}/{gem['address']}"
                    r = requests.get(order_url, timeout=5)
                    if r.status_code == 200:
                        orders = r.json()
                        if isinstance(orders, list):
                            has_paid_order = any(o.get("status") == "approved" for o in orders)
                except Exception:
                    pass
                gem["has_paid_order"] = has_paid_order
                
                # 2. Grade expected value score
                score = calculate_gem_score(gem, security)
                
                gem["security_status"] = security["status"]
                gem["security_flags"]  = security["flags"]
                gem["predator_score"]   = score
                processed.append(gem)
                
            # Sort final output by predator score descending
            processed.sort(key=lambda x: x["predator_score"], reverse=True)
            
            with _scan_lock:
                _scanned_gems = processed
                
            print(f"[DEXSCREENER PREDATOR] Scan complete. Found {len(processed)} gems. High score: {processed[0]['predator_score'] if processed else 0}", flush=True)
            
        except Exception as e:
            print(f"[DEXSCREENER PREDATOR] Loop error: {e}", flush=True)
            
        time.sleep(SCAN_INTERVAL_SEC)

# ============================================================================-
#  PUBLIC API & LIFECYCLE MANAGEMENT
# ============================================================================-

# ============================================================================-
#  HYBRID WEBSOCKET STREAM CLIENT
# ============================================================================-
_ws_threads = []

def _on_ws_message(ws, message):
    try:
        payload = json.loads(message)
        data = payload.get("data", [])
        if not isinstance(data, list):
            return
            
        for item in data:
            chain_id = item.get("chainId", "").lower()
            token_addr = item.get("tokenAddress")
            if chain_id in DEX_CHAINS and token_addr:
                # Fast-track check in background thread to avoid blocking WS loop
                threading.Thread(target=_process_websocket_token, args=(chain_id, token_addr), daemon=True).start()
    except Exception:
        pass

def _process_websocket_token(chain, address):
    global _scanned_gems
    try:
        # Check if already scanned recently to avoid redundancy
        with _scan_lock:
            if any(g["address"] == address for g in _scanned_gems):
                return
                
        # Perform instant security & grading scan
        gem = scan_custom_token(chain, address)
        if isinstance(gem, dict) and gem.get("predator_score", 0) >= 65: # Score threshold
            with _scan_lock:
                # Prevent duplication again
                if not any(g["address"] == address for g in _scanned_gems):
                    _scanned_gems.insert(0, gem)
                    _scanned_gems = _scanned_gems[:100] # Cap size
                    print(f"🔥 [WEBSOCKET FAST-TRACK] Captured high-momentum token: {gem.get('symbol', 'UNKNOWN')} | Score: {gem['predator_score']}", flush=True)
    except Exception:
        pass

def _run_websocket_client(url):
    global _is_running
    while _is_running:
        try:
            ws = websocket.WebSocketApp(
                url,
                on_message=_on_ws_message,
                on_error=lambda ws, err: None,
                on_close=lambda ws, close_status_code, close_msg: None
            )
            ws.run_forever()
        except Exception:
            pass
        time.sleep(5) # Reconnect delay

# ============================================================================-
#  PUBLIC API & LIFECYCLE MANAGEMENT
# ============================================================================-

def start_dex_hunter():
    """Starts the DexScreener Gem Finder scanning daemon with Hybrid WebSocket streams."""
    global _is_running, _scan_thread, _ws_threads
    if _is_running:
        return
        
    _is_running = True
    
    # 1. Start Polling Loop
    _scan_thread = threading.Thread(target=_scan_pipeline, daemon=True, name="DexPredator")
    _scan_thread.start()
    
    # 2. Start Real-time WebSocket Stream Listeners
    ws_urls = [
        "wss://api.dexscreener.com/token-profiles/recent-updates/v1",
        "wss://api.dexscreener.com/token-boosts/latest/v1"
    ]
    _ws_threads = []
    for url in ws_urls:
        t = threading.Thread(target=_run_websocket_client, args=(url,), daemon=True)
        t.start()
        _ws_threads.append(t)
        
    print("[DEXSCREENER PREDATOR] Scanner Daemon & Hybrid WebSocket Listeners started successfully.", flush=True)

def stop_dex_hunter():
    """Gracefully shuts down the scanning daemon and WebSocket listeners."""
    global _is_running
    _is_running = False
    print("[DEXSCREENER PREDATOR] Scanner Daemon & WebSocket Listeners stopped.", flush=True)

def get_scanned_gems() -> list:
    """Returns the globally audited and ranked gems list."""
    with _scan_lock:
        return list(_scanned_gems)

def scan_custom_token(chain: str, address: str) -> dict:
    """
    Exposes an instant target scan capability.
    Fetches the token details from DexScreener and performs a live security audit.
    """
    try:
        # 1. Fetch token details from DexScreener
        url = f"https://api.dexscreener.com/latest/dex/tokens/{address}"
        res = requests.get(url, timeout=10).json()
        pairs = res.get("pairs", []) or []
        
        if not pairs:
            # Fallback if pair details are not available yet (ultra new token profile)
            security = check_token_security(chain, address)
            return {
                "symbol": "NEW_TOKEN",
                "name": "NEW_TOKEN",
                "address": address,
                "price": 0,
                "volume_5m": 0,
                "liquidity": 0,
                "market_cap": 0,
                "security_status": security["status"],
                "security_flags": security["flags"],
                "predator_score": 30 + security["score_impact"]
            }
            
        # Get the primary pair (highest liquidity)
        pairs.sort(key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0), reverse=True)
        p = pairs[0]
        
        gem = {
            "chain": p.get("chainId", "").lower(),
            "symbol": p.get("baseToken", {}).get("symbol", "UNKNOWN"),
            "name": p.get("baseToken", {}).get("name", "UNKNOWN"),
            "address": address,
            "price": float(p.get("priceUsd", 0) or 0),
            "volume_5m": float(p.get("volume", {}).get("m5", 0) or 0),
            "volume_1h": float(p.get("volume", {}).get("h1", 0) or 0),
            "liquidity": float(p.get("liquidity", {}).get("usd", 0) or 0),
            "market_cap": float(p.get("marketCap", 0) or 0),
            "price_change_5m": float(p.get("priceChange", {}).get("m5", 0) or 0),
            "price_change_1h": float(p.get("priceChange", {}).get("h1", 0) or 0),
            "txns": p.get("txns", {}),
            "info": p.get("info", {})
        }
        
        # 2. Live Security Audit
        security = check_token_security(gem["chain"], address)
        score = calculate_gem_score(gem, security)
        
        gem["security_status"] = security["status"]
        gem["security_flags"]  = security["flags"]
        gem["predator_score"]   = score
        
        return gem
    except Exception as e:
        return {"status": "error", "message": f"Scan failed: {str(e)}"}
