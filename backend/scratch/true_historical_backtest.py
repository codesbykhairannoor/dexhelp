import os
import sys
import time
import requests
from dotenv import load_dotenv

# Ensure absolute import path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from dex_hunter import _fetch_candidates, check_token_security, calculate_gem_score

# Fix Windows terminal encoding for Emojis
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Load environmental variables
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
load_dotenv(os.path.join(parent_dir, '.env'))

def fetch_historical_candles(pool_address: str, limit: int = 100) -> list:
    """Fetch 1-minute historical candles from GeckoTerminal API."""
    url = f"https://api.geckoterminal.com/api/v2/networks/solana/pools/{pool_address}/ohlcv/minute?aggregate=1&limit={limit}"
    headers = {"Accept": "application/json;version=20230203"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            ohlcv_list = data.get("data", {}).get("attributes", {}).get("ohlcv_list", [])
            # Format is [timestamp, open, high, low, close, volume]
            ohlcv_list.reverse() # chronologically oldest first
            return ohlcv_list
    except Exception as e:
        print(f"  [WARN] Failed to fetch candles for pool {pool_address}: {e}")
    return []

def run_true_historical_backtest():
    print("=" * 115)
    print("🛸 DEX PREDATOR V13.5 - TRUE HISTORICAL STRATEGY COMPARATOR")
    print("   Comparing V8.6 vs V12.0 vs V13.5 (Moonshot Runner) on ACTUAL 1-Minute Past Candles from Solana Pools")
    print("=" * 115)
    
    # Step 1: Scan candidates
    print("[1] Fetching live candidates to identify trade opportunities...", flush=True)
    raw_candidates = _fetch_candidates()
    if not raw_candidates:
        print("❌ No candidates returned from DexScreener API. Aborting.")
        return
        
    print(f"  Fetched {len(raw_candidates)} raw candidates. Auditing safety & computing scores...", flush=True)
    
    eligible_tokens = []
    
    for gem in raw_candidates:
        addr = gem["address"]
        chain = gem["chain"]
        
        if chain.lower() != "solana":
            continue
            
        security = check_token_security(chain, addr)
        score = calculate_gem_score(gem, security)
        
        # Only buy if token matches our exact V13.0 trading criteria
        is_eligible = security["status"] in ["CLEAN & SAFE", "WARNINGS"] and score >= 65
        
        if is_eligible:
            dex_url = f"https://api.dexscreener.com/latest/dex/tokens/{addr}"
            try:
                r = requests.get(dex_url, timeout=5)
                if r.status_code == 200:
                    pairs = r.json().get("pairs", [])
                    if pairs:
                        pool_address = pairs[0].get("pairAddress")
                        gem["pool_address"] = pool_address
                        eligible_tokens.append(gem)
                        print(f"  ✅ {gem['symbol']:<10} | Score: {score}/100 | Pool: {pool_address}")
                        if len(eligible_tokens) >= 5: # Limit to 5 tokens for API efficiency
                            break
            except Exception:
                pass
        else:
            print(f"  ❌ {gem['symbol']:<10} | Safety: {security['status']:<12} | Score: {score}/100 (BLOCKED)")

    if not eligible_tokens:
        print("\n❌ No Solana tokens met the strict safety/scoring entry filters at this moment.")
        return

    print(f"\n[2] FETCHING ACTUAL MINUTE CANDLES FOR HISTORICAL BACKTEST ({len(eligible_tokens)} Tokens):")
    
    trade_alloc = 10.00 # Flat $10 trade allocation
    gas_fee = 0.01
    swap_fee_pct = 0.0025
    slippage_pct = 0.005
    cost_per_trade = gas_fee + (trade_alloc * swap_fee_pct) + (trade_alloc * slippage_pct)
    net_investment = trade_alloc - cost_per_trade
    
    results_v13_5 = []
    results_v12_0 = []
    results_v8_6 = []
    
    for gem in eligible_tokens:
        symbol = gem["symbol"]
        pool_addr = gem["pool_address"]
        
        print(f"  - Querying historical candles for {symbol} ({pool_addr})...", end="", flush=True)
        time.sleep(1) # Rate limit protection
        candles = fetch_historical_candles(pool_addr, limit=120) # Past 2 hours
        
        if not candles or len(candles) < 10:
            print(" FAILED (Insufficient candles)")
            continue
            
        print(f" SUCCESS ({len(candles)} candles found)")
        
        entry_price = candles[0][4] # Buy at Close of first candle
        qty = net_investment / entry_price
        
        # ----------------------------------------------------
        # Simulation A: V13.5 Predator Strategy (Moonshot Runner)
        # ----------------------------------------------------
        highest_price = entry_price
        v13_5_closed = False
        v13_5_pnl_pct = 0.0
        v13_5_exit_reason = "EXPIRED"
        
        for idx in range(1, len(candles)):
            c_high = candles[idx][2]
            c_low = candles[idx][3]
            c_close = candles[idx][4]
            
            highest_price = max(highest_price, c_high)
            price_gain_pct = ((highest_price - entry_price) / entry_price) * 100
            
            # V13.5 Strategy
            if price_gain_pct >= 400.0:
                sl_price = highest_price * 0.70
                exit_lbl = "STAGE 4 (400%+ -> 30% TSL)"
            elif price_gain_pct >= 150.0:
                sl_price = highest_price * 0.75
                exit_lbl = "STAGE 3 (150%+ -> 25% TSL)"
            elif price_gain_pct >= 60.0:
                sl_price = highest_price * 0.80
                exit_lbl = "STAGE 2 (60%+ -> 20% TSL)"
            elif price_gain_pct >= 30.0:
                sl_price = entry_price * 1.15
                exit_lbl = "STAGE 1 (+15% LOCK)"
            elif price_gain_pct >= 15.0:
                sl_price = entry_price * 1.02
                exit_lbl = "BE-LOCK (+2%)"
            else:
                sl_price = highest_price * 0.88  # SL 12%
                exit_lbl = "TRAILING SL (12%)"
                
            if c_low <= sl_price:
                v13_5_closed = True
                v13_5_pnl_pct = ((sl_price - entry_price) / entry_price) * 100
                v13_5_exit_reason = f"Hit {exit_lbl} @ Min {idx}"
                break
                
        if not v13_5_closed:
            v13_5_pnl_pct = ((candles[-1][4] - entry_price) / entry_price) * 100
            
        results_v13_5.append({"symbol": symbol, "pnl": v13_5_pnl_pct, "exit": v13_5_exit_reason})
        
        # ----------------------------------------------------
        # Simulation B: V12.0 Old Strategy (BE-Guard +3% Shakeout)
        # ----------------------------------------------------
        highest_price_12 = entry_price
        v12_closed = False
        v12_pnl_pct = 0.0
        v12_exit_reason = "EXPIRED"
        
        for idx in range(1, len(candles)):
            c_high = candles[idx][2]
            c_low = candles[idx][3]
            c_close = candles[idx][4]
            
            highest_price_12 = max(highest_price_12, c_high)
            price_gain_pct = ((highest_price_12 - entry_price) / entry_price) * 100
            
            # V12.0 Strategy
            if price_gain_pct >= 300.0:
                sl_price = highest_price_12 * 0.60
                exit_lbl = "STAGE 4 (+300% -> 40% TSL)"
            elif price_gain_pct >= 100.0:
                sl_price = highest_price_12 * 0.70
                exit_lbl = "STAGE 3 (+100% -> 30% TSL)"
            elif price_gain_pct >= 50.0:
                sl_price = entry_price * 1.35
                exit_lbl = "STAGE 2 (+35% LOCK)"
            elif price_gain_pct >= 20.0:
                sl_price = entry_price * 1.10
                exit_lbl = "STAGE 1 (+10% LOCK)"
            elif price_gain_pct >= 4.0:
                sl_price = entry_price * 1.03  # Shakeout BE-Guard +3%
                exit_lbl = "BE-GUARD (+3%)"
            else:
                sl_price = highest_price_12 * 0.80 # Initial SL 20%
                exit_lbl = "TRAILING SL (20%)"
                
            if c_low <= sl_price:
                v12_closed = True
                v12_pnl_pct = ((sl_price - entry_price) / entry_price) * 100
                v12_exit_reason = f"Hit {exit_lbl} @ Min {idx}"
                break
                
        if not v12_closed:
            v12_pnl_pct = ((candles[-1][4] - entry_price) / entry_price) * 100
            
        results_v12_0.append({"symbol": symbol, "pnl": v12_pnl_pct, "exit": v12_exit_reason})
        
        # ----------------------------------------------------
        # Simulation C: V8.6 Old Strategy (Fixed 30% TP, 20% SL)
        # ----------------------------------------------------
        v8_closed = False
        v8_pnl_pct = 0.0
        v8_exit_reason = "EXPIRED"
        
        for idx in range(1, len(candles)):
            c_high = candles[idx][2]
            c_low = candles[idx][3]
            
            high_gain = ((c_high - entry_price) / entry_price) * 100
            low_gain = ((c_low - entry_price) / entry_price) * 100
            
            if high_gain >= 30.0:
                v8_closed = True
                v8_pnl_pct = 30.0
                v8_exit_reason = f"Hit Fixed TP (+30%) @ Min {idx}"
                break
            elif low_gain <= -20.0:
                v8_closed = True
                v8_pnl_pct = -20.0
                v8_exit_reason = f"Hit Fixed SL (-20%) @ Min {idx}"
                break
                
        if not v8_closed:
            v8_pnl_pct = ((candles[-1][4] - entry_price) / entry_price) * 100
            
        results_v8_6.append({"symbol": symbol, "pnl": v8_pnl_pct, "exit": v8_exit_reason})

    if not results_v13_5:
        print("\n❌ Failed to process backtest.")
        return

    # Step 5: Comparative Display
    print("\n" + "=" * 115)
    print("🏆 FINAL COMPARATIVE AUDIT: THREE-GENERATION STRATEGY PERFORMANCE")
    print("=" * 115)
    
    total_pnl_13_5 = sum(r["pnl"] for r in results_v13_5)
    wins_13_5 = sum(1 for r in results_v13_5 if r["pnl"] >= 0)
    wr_13_5 = (wins_13_5 / len(results_v13_5)) * 100
    
    total_pnl_12 = sum(r["pnl"] for r in results_v12_0)
    wins_12 = sum(1 for r in results_v12_0 if r["pnl"] >= 0)
    wr_12 = (wins_12 / len(results_v12_0)) * 100
    
    total_pnl_8 = sum(r["pnl"] for r in results_v8_6)
    wins_8 = sum(1 for r in results_v8_6 if r["pnl"] >= 0)
    wr_8 = (wins_8 / len(results_v8_6)) * 100
    
    print(f"{'STRATEGY VERSION':<35} | {'TOTAL CUMULATIVE PnL':<22} | {'WIN RATE %':<12} | {'SAMPLES'}")
    print("-" * 115)
    print(f"{'🏆 V13.5 PREDATOR (Moonshot Runner)':<35} | {total_pnl_13_5:+.2f}% | {wr_13_5:.1f}% | {len(results_v13_5)} Tokens")
    print(f"{'V12.0 PREDATOR (BE-Guard +3% Shake)':<35} | {total_pnl_12:+.2f}% | {wr_12:.1f}% | {len(results_v12_0)} Tokens")
    print(f"{'OLD BOT V8.6 (Fixed TP/SL)':<35} | {total_pnl_8:+.2f}% | {wr_8:.1f}% | {len(results_v8_6)} Tokens")
    print("-" * 115)
    
    print("\n🔍 INDIVIDUAL SAMPLE HISTORICAL REPORT:")
    for r13_5, r12, r8 in zip(results_v13_5, results_v12_0, results_v8_6):
        print(f"\n🪙 TOKEN: {r13_5['symbol']}")
        print(f"  -> V13.5 (Moonshot Runner) PnL : {r13_5['pnl']:+.2f}% | Exit: {r13_5['exit']}")
        print(f"  -> V12.0 (BE-Guard Shakeout) PnL : {r12['pnl']:+.2f}% | Exit: {r12['exit']}")
        print(f"  -> V8.6 (Old Fixed TP/SL) PnL    : {r8['pnl']:+.2f}% | Exit: {r8['exit']}")
    print("=" * 115)

if __name__ == "__main__":
    run_true_historical_backtest()
