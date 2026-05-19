import os
import json
import websocket
import requests
import time
import threading
from collections import defaultdict

# ============================================================================-
#  CONFIG & INITIALIZATION
# ============================================================================-
SCAN_INTERVAL_SEC     = 60     # Scan DexScreener every 1 minute
MIN_LIQUIDITY_USD     = 10000  # Minimum $10k liquidity for safety
MIN_MCAP_USD          = 15000  # Minimum $15k marketcap to filter dust
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
        try:
            rug_url = f"https://api.rugcheck.xyz/v1/tokens/{address}/report"
            r = requests.get(rug_url, timeout=5)
            if r.status_code == 200:
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
        except Exception:
            pass # Silently fall back to GoPlus if RugCheck times out or is throttled

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

    # NEW SIGNAL 1: Token Age Window (Optimal Entry Timing)
    # Too young = developer can still rug. Too old = pump already over.
    age_sec = pair_data.get("age_estimate_sec", 3600)
    if 900 <= age_sec <= 21600:   # Sweet spot: 15 min - 6 hours
        score += 20
    elif age_sec < 900:           # < 15 minutes: dangerously early
        score -= 40
    elif age_sec > 86400:         # > 24 hours: momentum likely exhausted
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
    
    # A. FOMO Shield: Anti-Top Buying (Vertical lines are dangerous!)
    if p5m > 150.0 or p1h > 500.0:
        score -= 25 # Highly overbought! Deduct points to prevent buying the top.
    
    # B. Consolidation Support Finder (Optimal pullback buy point)
    elif 30.0 <= p1h <= 200.0 and -15.0 <= p5m <= 20.0:
        score += 10 # Healthy pullback/consolidation. Great entry point!
        
    # C. Severe Dump Protection (Falling knife safety)
    elif p5m < -40.0:
        score -= 20 # Avoid panic selling momentum.

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
    """Queries DexScreener API for new and trending tokens using Token Boosts & Profiles."""
    global _verified_profiles, _boost_tracker
    candidates = {}
    
    profiles_list = []
    takeovers_list = []

    # 1. Update Verified Profiles, Community Takeovers & Trending Metas
    try:
        profile_url = "https://api.dexscreener.com/token-profiles/latest/v1"
        res = requests.get(profile_url, timeout=5)
        if res.status_code == 200:
            profiles_list = res.json()
            if isinstance(profiles_list, list):
                _verified_profiles = {p.get("tokenAddress") for p in profiles_list if p.get("tokenAddress")}
    except Exception as e:
        print(f"[DEX HUNTER] Profile list fetch failed: {e}")

    # NEW SIGNAL 4: Community Takeover tokens (Bullish revival narrative)
    global _community_takeover_tokens
    try:
        takeover_url = "https://api.dexscreener.com/community-takeovers/latest/v1"
        res = requests.get(takeover_url, timeout=5)
        if res.status_code == 200:
            takeovers_list = res.json()
            if isinstance(takeovers_list, list):
                _community_takeover_tokens = {t.get("tokenAddress") for t in takeovers_list if t.get("tokenAddress")}
    except Exception as e:
        print(f"[DEX HUNTER] Community takeover fetch failed: {e}")

    global _trending_metas
    try:
        meta_url = "https://api.dexscreener.com/metas/trending/v1"
        res = requests.get(meta_url, timeout=5)
        if res.status_code == 200:
            metas = res.json()
            if isinstance(metas, list):
                _trending_metas = [m.get("slug", "").lower() for m in metas if m.get("slug")]
    except Exception as e:
        print(f"[DEX HUNTER] Trending metas list fetch failed: {e}")

    # 2. Fetch from Token Boosts (Latest & Top)
    boost_urls = [
        "https://api.dexscreener.com/token-boosts/latest/v1",
        "https://api.dexscreener.com/token-boosts/top/v1"
    ]
    
    addresses_to_scan = []
    
    # Golden Funnel A: Extract from Token Boosts
    for url in boost_urls:
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                boosted = res.json()
                if isinstance(boosted, list):
                    for b in boosted:
                        chain_id = b.get("chainId", "").lower()
                        if chain_id in DEX_CHAINS:
                            addr = b.get("tokenAddress")
                            if addr:
                                # V13.1 GOLDEN FACT: Use totalAmount representing cumulative boost weight (viral factor)
                                _boost_tracker[addr] = int(b.get("totalAmount", 0) or b.get("amount", 0) or 0)
                                if (chain_id, addr) not in addresses_to_scan:
                                    addresses_to_scan.append((chain_id, addr))
        except Exception as e:
            print(f"[DEX HUNTER] Boost fetch failed: {e}")
            
    # Golden Funnel B: Inject Token Profiles to addresses_to_scan
    try:
        if isinstance(profiles_list, list):
            for p in profiles_list:
                chain_id = p.get("chainId", "").lower()
                if chain_id in DEX_CHAINS:
                    addr = p.get("tokenAddress")
                    if addr and (chain_id, addr) not in addresses_to_scan:
                        addresses_to_scan.append((chain_id, addr))
    except Exception:
        pass

    # Golden Funnel C: Inject Community Takeovers to addresses_to_scan
    try:
        if isinstance(takeovers_list, list):
            for t in takeovers_list:
                chain_id = t.get("chainId", "").lower()
                if chain_id in DEX_CHAINS:
                    addr = t.get("tokenAddress")
                    if addr and (chain_id, addr) not in addresses_to_scan:
                        addresses_to_scan.append((chain_id, addr))
    except Exception:
        pass

    # Limit to 80 addresses to maximize candidate pool
    addresses_to_scan = list({(c, a) for c, a in addresses_to_scan})[:80]
    
    # 3. Fetch full pair details & run Multi-Pool Liquidity Aggregator
    for chain_id, addr in addresses_to_scan:
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{addr}"
            res = requests.get(url, timeout=10).json()
            pairs = res.get("pairs", []) or []
            
            if not pairs:
                continue
                
            # Filter pairs of the target chain and run aggregation
            chain_pairs = [p for p in pairs if p.get("chainId", "").lower() == chain_id]
            if not chain_pairs:
                continue
                
            # Sort by liquidity descending to identify primary pool
            chain_pairs.sort(key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0), reverse=True)
            primary_p = chain_pairs[0]
            
            # Aggregate total liquidity across all pools on the chain
            aggregated_liquidity = sum(float(p.get("liquidity", {}).get("usd", 0) or 0) for p in chain_pairs)
            mcap = float(primary_p.get("marketCap", 0) or 0)
            
            # V13.0 L/MC Ratio Calculation & Filtering
            l_mc_ratio = (aggregated_liquidity / mcap) if mcap > 0 else 0
            
            # V13.0 Buy/Sell Transaction Velocity Ratio (BS-Ratio)
            tx_5m = primary_p.get("txns", {}).get("m5", {})
            buys = int(tx_5m.get("buys", 0))
            sells = int(tx_5m.get("sells", 0))
            bs_ratio = (buys / (buys + sells)) if (buys + sells) > 0 else 0.50
            
            # Apply strict V13.0 Quantitative Filters
            if (aggregated_liquidity >= MIN_LIQUIDITY_USD and 
                mcap >= MIN_MCAP_USD and mcap <= MAX_MCAP_USD and
                0.08 <= l_mc_ratio <= 0.25 and
                bs_ratio >= 0.65):
                candidates[addr] = {
                    "chain": chain_id,
                    "pair_address": primary_p.get("pairAddress", ""),
                    "symbol": primary_p.get("baseToken", {}).get("symbol", "UNKNOWN"),
                    "name": primary_p.get("baseToken", {}).get("name", "UNKNOWN"),
                    "address": addr,
                    "price": float(primary_p.get("priceUsd", 0) or 0),
                    "volume_5m": float(primary_p.get("volume", {}).get("m5", 0) or 0),
                    "volume_1h": float(primary_p.get("volume", {}).get("h1", 0) or 0),
                    "volume_24h": float(primary_p.get("volume", {}).get("h24", 0) or 0),  # NEW: for volume acceleration
                    "liquidity": aggregated_liquidity,
                    "market_cap": mcap,
                    "fdv": float(primary_p.get("fdv", 0) or 0),  # NEW: for FDV inflation ratio
                    "price_change_5m": float(primary_p.get("priceChange", {}).get("m5", 0) or 0),
                    "price_change_1h": float(primary_p.get("priceChange", {}).get("h1", 0) or 0),
                    "txns": primary_p.get("txns", {}),
                    "info": primary_p.get("info", {}),
                    "url": primary_p.get("url", ""),
                    "boost_amount": _boost_tracker.get(addr, 0),
                    "boosts_active": int(primary_p.get("boosts", {}).get("active", 0) or 0),  # NEW: active boosts
                    "age_estimate_sec": int(time.time() - (float(primary_p.get("pairCreatedAt", 0)) / 1000)) if primary_p.get("pairCreatedAt") else 3600
                }
        except Exception as e:
            pass

    # EXPANDED MULTI-SOURCE SEARCH (Always run, not just as fallback)
    # 12 targeted queries to massively widen the candidate funnel
    SEARCH_QUERIES = [
        "solana", "pump", "pepe", "doge", "moon", "ape",
        "meme", "cat", "dog", "ai", "based", "new"
    ]
    for query in SEARCH_QUERIES:
        try:
            url = f"https://api.dexscreener.com/latest/dex/search?q={query}"
            res = requests.get(url, timeout=10).json()
            pairs = res.get("pairs", []) or []
            
            for p in pairs:
                chain_id = p.get("chainId", "").lower()
                if chain_id not in DEX_CHAINS:
                    continue
                
                addr = p.get("baseToken", {}).get("address", "")
                if not addr or addr in candidates:
                    continue
                liq = float(p.get("liquidity", {}).get("usd", 0) or 0)
                mcap = float(p.get("marketCap", 0) or 0)
                
                # V13.0 L/MC Ratio Calculation & Filtering
                l_mc_ratio = (liq / mcap) if mcap > 0 else 0
                
                # V13.0 Buy/Sell Transaction Velocity Ratio (BS-Ratio)
                tx_5m = p.get("txns", {}).get("m5", {})
                buys = int(tx_5m.get("buys", 0))
                sells = int(tx_5m.get("sells", 0))
                bs_ratio = (buys / (buys + sells)) if (buys + sells) > 0 else 0.50
                
                if (addr and liq >= MIN_LIQUIDITY_USD and 
                    mcap >= MIN_MCAP_USD and mcap <= MAX_MCAP_USD and
                    0.08 <= l_mc_ratio <= 0.25 and
                    bs_ratio >= 0.65):
                    age_sec = int(time.time() - (float(p.get("pairCreatedAt", 0)) / 1000)) if p.get("pairCreatedAt") else 3600
                    candidates[addr] = {
                        "chain": chain_id,
                        "pair_address": p.get("pairAddress", ""),
                        "symbol": p.get("baseToken", {}).get("symbol", "UNKNOWN"),
                        "name": p.get("baseToken", {}).get("name", "UNKNOWN"),
                        "address": addr,
                        "price": float(p.get("priceUsd", 0) or 0),
                        "volume_5m": float(p.get("volume", {}).get("m5", 0) or 0),
                        "volume_1h": float(p.get("volume", {}).get("h1", 0) or 0),
                        "volume_24h": float(p.get("volume", {}).get("h24", 0) or 0),
                        "liquidity": liq,
                        "market_cap": mcap,
                        "fdv": float(p.get("fdv", 0) or 0),
                        "price_change_5m": float(p.get("priceChange", {}).get("m5", 0) or 0),
                        "price_change_1h": float(p.get("priceChange", {}).get("h1", 0) or 0),
                        "txns": p.get("txns", {}),
                        "info": p.get("info", {}),
                        "url": p.get("url", ""),
                        "boost_amount": _boost_tracker.get(addr, 0),
                        "boosts_active": int(p.get("boosts", {}).get("active", 0) or 0),
                        "age_estimate_sec": age_sec
                    }
        except Exception:
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
