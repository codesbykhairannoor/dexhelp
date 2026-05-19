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
            # API returns newest first. Reverse to chronological order (oldest first)
            ohlcv_list.reverse()
            return ohlcv_list
    except Exception as e:
        print(f"  [WARN] Failed to fetch candles for pool {pool_address}: {e}")
    return []

def run_true_historical_backtest():
    print("=" * 110)
    print("🛸 DEX PREDATOR V13.2 - TRUE HISTORICAL MARKET BACKTEST ENGINE")
    print("   Evaluating V13.0 vs V8.6 strategies on ACTUAL 1-Minute Past Candles from Solana On-Chain Pools")
    print("=" * 110)
    
    # Step 1: Scan candidates from DexScreener using actual bot logic
    print("[1] Fetching live candidates to identify trade opportunities...", flush=True)
    raw_candidates = _fetch_candidates()
    if not raw_candidates:
        print("❌ No candidates returned from DexScreener boosts/profiles API. Aborting.")
        return
        
    print(f"  Fetched {len(raw_candidates)} raw candidates. Auditing safety & computing scores...", flush=True)
    
    eligible_tokens = []
    
    for gem in raw_candidates:
        addr = gem["address"]
        chain = gem["chain"]
        
        if chain.lower() != "solana":
            continue
            
        # Perform dynamic security audit
        security = check_token_security(chain, addr)
        score = calculate_gem_score(gem, security)
        
        # Only buy if token matches our exact V13.0 trading criteria
        is_eligible = security["status"] in ["CLEAN & SAFE", "WARNINGS"] and score >= 65
        
        if is_eligible:
            # Query pool address from pairs list to fetch candles from GeckoTerminal
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
    net_investment = trade_alloc - cost_per_trade # Actual capital traded
    
    results_v13 = []
    results_v8 = []
    
    for gem in eligible_tokens:
        symbol = gem["symbol"]
        pool_addr = gem["pool_address"]
        
        print(f"  - Querying historical candles for {symbol} ({pool_addr})...", end="", flush=True)
        time.sleep(1) # Rate limit protection for public GeckoTerminal endpoint
        candles = fetch_historical_candles(pool_addr, limit=120) # Fetch past 2 hours
        
        if not candles or len(candles) < 10:
            print(" FAILED (Insufficient candles)")
            continue
            
        print(f" SUCCESS ({len(candles)} candles found)")
        
        # Chronological simulation
        entry_price = candles[0][4] # Buy at Close of the first candle
        qty = net_investment / entry_price
        
        # ----------------------------------------------------
        # Simulation A: V13.0 Predator Strategy (Trailing SL)
        # ----------------------------------------------------
        highest_price = entry_price
        v13_closed = False
        v13_pnl_pct = 0.0
        v13_exit_reason = "EXPIRED (Still Active)"
        
        # Evaluate subsequent candles
        for idx in range(1, len(candles)):
            c_high = candles[idx][2]
            c_low = candles[idx][3]
            c_close = candles[idx][4]
            
            # Update price high-water mark
            highest_price = max(highest_price, c_high)
            price_gain_pct = ((highest_price - entry_price) / entry_price) * 100
            
            # Stage evaluation
            if price_gain_pct >= 300.0:
                sl_price = highest_price * 0.60
                exit_lbl = "STAGE 4 (+300% -> 40% TSL)"
            elif price_gain_pct >= 100.0:
                sl_price = highest_price * 0.70
                exit_lbl = "STAGE 3 (+100% -> 30% TSL)"
            elif price_gain_pct >= 50.0:
                sl_price = entry_price * 1.35
                exit_lbl = "STAGE 2 (+35% LOCK)"
            elif price_gain_pct >= 20.0:
                sl_price = entry_price * 1.10
                exit_lbl = "STAGE 1 (+10% LOCK)"
            elif price_gain_pct >= 4.0:
                sl_price = entry_price * 1.03
                exit_lbl = "BE-GUARD (+3%)"
            else:
                sl_price = highest_price * 0.80
                exit_lbl = "TRAILING SL (20%)"
                
            # Check if lowest price of candle hit SL price
            if c_low <= sl_price:
                v13_closed = True
                v13_pnl_pct = ((sl_price - entry_price) / entry_price) * 100
                v13_exit_reason = f"Hit {exit_lbl} @ Minute {idx}"
                break
                
        if not v13_closed:
            # If never hit SL/TSL, close at last candle close
            v13_pnl_pct = ((candles[-1][4] - entry_price) / entry_price) * 100
            
        results_v13.append({
            "symbol": symbol,
            "pnl": v13_pnl_pct,
            "exit": v13_exit_reason
        })
        
        # ----------------------------------------------------
        # Simulation B: V8.6 Old Strategy (Fixed 30% TP, 20% SL)
        # ----------------------------------------------------
        v8_closed = False
        v8_pnl_pct = 0.0
        v8_exit_reason = "EXPIRED (Still Active)"
        
        for idx in range(1, len(candles)):
            c_high = candles[idx][2]
            c_low = candles[idx][3]
            c_close = candles[idx][4]
            
            # Check if high hits fixed TP (+30%)
            high_gain = ((c_high - entry_price) / entry_price) * 100
            low_gain = ((c_low - entry_price) / entry_price) * 100
            
            if high_gain >= 30.0:
                v8_closed = True
                v8_pnl_pct = 30.0
                v8_exit_reason = f"Hit Fixed TP (+30%) @ Minute {idx}"
                break
            elif low_gain <= -20.0:
                v8_closed = True
                v8_pnl_pct = -20.0
                v8_exit_reason = f"Hit Fixed SL (-20%) @ Minute {idx}"
                break
                
        if not v8_closed:
            v8_pnl_pct = ((candles[-1][4] - entry_price) / entry_price) * 100
            
        results_v8.append({
            "symbol": symbol,
            "pnl": v8_pnl_pct,
            "exit": v8_exit_reason
        })

    if not results_v13:
        print("\n❌ Failed to construct backtest files due to API query limits. Try again later.")
        return

    # Step 5: Comparative Display
    print("\n" + "=" * 110)
    print("🏆 FINAL COMPARATIVE AUDIT: V13.0 PREDATOR ULTIMATE vs OLD V8.6 STRATEGY (ACTUAL PAST CANDLES)")
    print("=" * 110)
    
    total_pnl_13 = sum(r["pnl"] for r in results_v13)
    wins_13 = sum(1 for r in results_v13 if r["pnl"] >= 0)
    wr_13 = (wins_13 / len(results_v13)) * 100
    
    total_pnl_8 = sum(r["pnl"] for r in results_v8)
    wins_8 = sum(1 for r in results_v8 if r["pnl"] >= 0)
    wr_8 = (wins_8 / len(results_v8)) * 100
    
    print(f"{'STRATEGY':<30} | {'TOTAL CUMULATIVE PnL':<22} | {'WIN RATE %':<12} | {'SAMPLES'}")
    print("-" * 110)
    print(f"{'🏆 V13.0 PREDATOR ULTIMATE':<30} | {total_pnl_13:+.2f}% | {wr_13:.1f}% | {len(results_v13)} Tokens")
    print(f"{'OLD BOT V8.6 (Fixed TP/SL)':<30} | {total_pnl_8:+.2f}% | {wr_8:.1f}% | {len(results_v8)} Tokens")
    print("-" * 110)
    
    print("\n🔍 INDIVIDUAL SAMPLE HISTORICAL REPORT:")
    print(f"{'SYMBOL':<10} | {'V13.0 PnL':<15} | {'V13.0 EXIT REASON':<28} | {'V8.6 PnL':<15} | {'V8.6 EXIT REASON'}")
    print("-" * 110)
    for r13, r8 in zip(results_v13, results_v8):
        p13_str = f"{r13['pnl']:+.2f}%"
        p8_str = f"{r8['pnl']:+.2f}%"
        print(f"{r13['symbol']:<10} | {p13_str:<15} | {r13['exit']:<28} | {p8_str:<15} | {r8['exit']}")
    print("=" * 110)

if __name__ == "__main__":
    run_true_historical_backtest()
