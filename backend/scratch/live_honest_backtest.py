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

# Load environmental variables from parent dir
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
load_dotenv(os.path.join(parent_dir, '.env'))

def get_live_prices(addresses: list) -> dict:
    """Fetch live prices from Jupiter Price V3 using our new Dual-Parsing logic."""
    jup_api_key = os.getenv("JUPITER_API_KEY")
    url = f"https://api.jup.ag/price/v3?ids={','.join(addresses)}"
    headers = {"x-api-key": jup_api_key} if jup_api_key else {}
    
    price_map = {}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            res = r.json()
            for addr in addresses:
                tinfo = res.get("data", {}).get(addr, {}) if "data" in res else res.get(addr, {})
                price = tinfo.get("usdPrice")
                if price is not None:
                    price_map[addr] = float(price)
    except Exception as e:
        print(f"  [WARN] Failed to fetch live prices: {e}")
    return price_map

def run_live_honest_backtest():
    print("=" * 110)
    print("🛰️  DEX PREDATOR V13.2 - HONEST REAL-TIME LIVE MARKET BACKTEST")
    print("   Scanning current DexScreener candidates and tracking prices live from Solana on-chain feed!")
    print("=" * 110)
    
    # Step 1: Scan candidates
    print("[1] Scanning candidates from DexScreener (Token Boosts, Profiles & Community Takeovers)...", flush=True)
    all_candidates = _fetch_candidates()
    if not all_candidates:
        print("❌ No candidates returned from DexScreener boosts/profiles API. Aborting.")
        return
        
    print(f"  Found {len(all_candidates)} raw network candidates. Filtering & Auditing security...", flush=True)
    
    selected_gems = []
    # Filter candidates based on actual bot entry filters (score >= 65, safety CLEAN/WARNINGS)
    for gem in all_candidates:
        addr = gem["address"]
        chain = gem["chain"]
        
        # Only Solana tokens for live Jupiter price feed compatibility in this test
        if chain.lower() != "solana":
            continue
            
        security = check_token_security(chain, addr)
        score = calculate_gem_score(gem, security)
        
        # Check safety and score threshold
        is_eligible = security["status"] in ["CLEAN & SAFE", "WARNINGS"] and score >= 65
        status_symbol = "✅" if is_eligible else "❌"
        print(f"  {status_symbol} {gem['symbol']:<10} | Safety: {security['status']:<12} | Score: {score:<3}/100 | LP: ${gem.get('liquidity',0):,.0f} | age: {gem.get('age_estimate_sec',0)//60}m")
        
        if is_eligible:
            selected_gems.append(gem)
            # Limit to 5 gems to avoid flooding pricing API
            if len(selected_gems) >= 5:
                break
                
    if not selected_gems:
        print("❌ No eligible Solana candidates met our strict V13.0 criteria (Score >= 65, SAFE) at this moment. Please try again in a few minutes.")
        return
        
    print(f"\n[2] SELECTED GEMS FOR TRADING SIMULATION ({len(selected_gems)} Tokens):")
    for gem in selected_gems:
        print(f"  - {gem['symbol']} ({gem['address']}) | Entry Price: ${gem['price']:.8f}")
        
    # Initialize simulation states
    # We allocate $10 per position
    trade_alloc = 10.00
    
    # Real-time state trackers for both strategies
    positions_v13 = []
    positions_v8 = []
    
    # Fetch initial exact live prices from Jupiter Price API V3 as baseline
    addresses = [gem["address"] for gem in selected_gems]
    initial_prices = get_live_prices(addresses)
    
    for gem in selected_gems:
        addr = gem["address"]
        base_price = initial_prices.get(addr, gem["price"])
        
        # V13.0 State: Uses Multi-Stage Trailing SL
        positions_v13.append({
            "symbol": gem["symbol"],
            "address": addr,
            "entry_price": base_price,
            "highest_price": base_price,
            "qty": trade_alloc / base_price,
            "status": "ACTIVE",
            "pnl_pct": 0.0,
            "exit_reason": "N/A"
        })
        
        # V8.6 State: Uses Fixed TP 30%, SL 20%
        positions_v8.append({
            "symbol": gem["symbol"],
            "address": addr,
            "entry_price": base_price,
            "qty": trade_alloc / base_price,
            "status": "ACTIVE",
            "pnl_pct": 0.0,
            "exit_reason": "N/A"
        })
        
    print("\n[3] STARTING LIVE PRICE ACCELERATED TRACKING LEDGER (5 Minutes, 15-second cycles):")
    print("-" * 110)
    
    cycles = 20 # 20 * 15 seconds = 5 minutes of real-time trading
    
    for c in range(1, cycles + 1):
        print(f"\n🌀 Cycle {c}/{cycles} | {time.strftime('%H:%M:%S')} | Fetching current on-chain prices...")
        time.sleep(15) # Wait 15s between cycles
        
        live_prices = get_live_prices(addresses)
        if not live_prices:
            print("  [WARN] Failed to get live prices for this cycle. Retrying in next cycle.")
            continue
            
        # 3.1 Evaluate V13.0 (Trailing SL + BE Guard)
        active_count_13 = 0
        for pos in positions_v13:
            if pos["status"] != "ACTIVE":
                continue
                
            addr = pos["address"]
            current_price = live_prices.get(addr)
            if not current_price:
                continue
                
            active_count_13 += 1
            entry = pos["entry_price"]
            
            # Update high watermark
            pos["highest_price"] = max(pos["highest_price"], current_price)
            highest = pos["highest_price"]
            
            price_gain_pct = ((highest - entry) / entry) * 100
            current_pnl_pct = ((current_price - entry) / entry) * 100
            
            # Multi-stage trailing SL limits
            if price_gain_pct >= 300.0:
                sl_price = highest * 0.60
                guard = "STAGE 4 (+300% -> 40% TSL)"
            elif price_gain_pct >= 100.0:
                sl_price = highest * 0.70
                guard = "STAGE 3 (+100% -> 30% TSL)"
            elif price_gain_pct >= 50.0:
                sl_price = entry * 1.35
                guard = "STAGE 2 (+35% LOCK)"
            elif price_gain_pct >= 20.0:
                sl_price = entry * 1.10
                guard = "STAGE 1 (+10% LOCK)"
            elif price_gain_pct >= 4.0:
                sl_price = entry * 1.03
                guard = "BE-GUARD (+3%)"
            else:
                sl_price = highest * 0.80
                guard = "TRAILING SL (20%)"
                
            # Exit evaluation
            if current_price <= sl_price:
                pos["status"] = "CLOSED"
                pos["pnl_pct"] = ((sl_price - entry) / entry) * 100
                pos["exit_reason"] = guard
                print(f"  💥 [V13 EXIT] {pos['symbol']} hit {guard}! Locked PnL: {pos['pnl_pct']:+.2f}%")
            else:
                pos["pnl_pct"] = current_pnl_pct
                
        # 3.2 Evaluate V8.6 (Fixed TP 30%, SL 20%)
        active_count_8 = 0
        for pos in positions_v8:
            if pos["status"] != "ACTIVE":
                continue
                
            addr = pos["address"]
            current_price = live_prices.get(addr)
            if not current_price:
                continue
                
            active_count_8 += 1
            entry = pos["entry_price"]
            current_pnl_pct = ((current_price - entry) / entry) * 100
            
            # Fixed TP/SL Check
            if current_pnl_pct >= 30.0:
                pos["status"] = "CLOSED"
                pos["pnl_pct"] = 30.0
                pos["exit_reason"] = "FIXED TP (+30%)"
                print(f"  🎯 [V8.6 EXIT] {pos['symbol']} hit FIXED TP! Locked PnL: +30.00%")
            elif current_pnl_pct <= -20.0:
                pos["status"] = "CLOSED"
                pos["pnl_pct"] = -20.0
                pos["exit_reason"] = "FIXED SL (-20%)"
                print(f"  💀 [V8.6 EXIT] {pos['symbol']} hit FIXED SL! Locked PnL: -20.00%")
            else:
                pos["pnl_pct"] = current_pnl_pct
                
        # Print status of active positions
        print("  Active Positions Update:")
        for pos13, pos8 in zip(positions_v13, positions_v8):
            stat13 = f"{pos13['pnl_pct']:+.2f}% ({pos13['status']})"
            stat8 = f"{pos8['pnl_pct']:+.2f}% ({pos8['status']})"
            print(f"    - {pos13['symbol']:<10} | V13.0 PnL: {stat13:<20} | V8.6 PnL: {stat8}")
            
        if active_count_13 == 0 and active_count_8 == 0:
            print("  [SYSTEM] All positions closed in both strategies. Ending simulation early!")
            break
            
    # Step 4: Display comparative results
    print("\n" + "=" * 110)
    print("🏆 FINAL COMPARATIVE AUDIT: V13.0 PREDATOR ULTIMATE vs OLD V8.6 STRATEGY")
    print("=" * 110)
    
    # Calculate V13.0 Results
    closed_v13 = [p for p in positions_v13]
    total_pnl_v13 = sum(p["pnl_pct"] for p in closed_v13)
    wins_v13 = sum(1 for p in closed_v13 if p["pnl_pct"] >= 0)
    wr_v13 = (wins_v13 / len(closed_v13)) * 100
    
    # Calculate V8.6 Results
    closed_v8 = [p for p in positions_v8]
    total_pnl_v8 = sum(p["pnl_pct"] for p in closed_v8)
    wins_v8 = sum(1 for p in closed_v8 if p["pnl_pct"] >= 0)
    wr_v8 = (wins_v8 / len(closed_v8)) * 100
    
    print(f"{'STRATEGY':<30} | {'TOTAL PnL %':<15} | {'WIN RATE %':<12} | {'CLOSED TRADES'}")
    print("-" * 110)
    print(f"{'🏆 V13.0 PREDATOR ULTIMATE':<30} | {total_pnl_v13:+.2f}% | {wr_v13:.1f}% | {len(closed_v13)} Trades")
    print(f"{'OLD BOT V8.6 (Fixed TP/SL)':<30} | {total_pnl_v8:+.2f}% | {wr_v8:.1f}% | {len(closed_v8)} Trades")
    print("-" * 110)
    
    print("\n🔍 INDIVIDUAL TOKEN REPORT:")
    print(f"{'SYMBOL':<10} | {'V13.0 FINAL PnL':<18} | {'V13.0 EXIT REASON':<25} | {'V8.6 FINAL PnL':<18} | {'V8.6 EXIT REASON'}")
    print("-" * 110)
    for pos13, pos8 in zip(positions_v13, positions_v8):
        p13_str = f"{pos13['pnl_pct']:+.2f}%"
        p8_str = f"{pos8['pnl_pct']:+.2f}%"
        print(f"{pos13['symbol']:<10} | {p13_str:<18} | {pos13['exit_reason']:<25} | {p8_str:<18} | {pos8['exit_reason']}")
    print("=" * 110)

if __name__ == "__main__":
    run_live_honest_backtest()
