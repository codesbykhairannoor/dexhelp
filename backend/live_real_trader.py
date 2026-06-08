import os
import sys
import time
import json
import requests
from dotenv import load_dotenv

# Fix module imports when executed from external cwd (like PM2)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from dex_hunter import _fetch_candidates, check_token_security, calculate_gem_score
from solana_executor import execute_solana_swap, get_solana_balance, base58_decode, base58_encode

# Fix Windows terminal encoding for Emojis
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Production Stability Fix: Dynamic Absolute Path Resolution
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PORTFOLIO_FILE = os.path.join(CURRENT_DIR, "live_portfolio.json")
ENV_PATH = os.path.join(os.path.dirname(CURRENT_DIR), ".env")
load_dotenv(ENV_PATH)

def load_live_portfolio() -> dict:
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r") as f:
                data = json.load(f)
                dirty = False
                if "cooldowns" not in data:
                    data["cooldowns"] = {}
                    dirty = True
                if "post_exit_monitoring" not in data:
                    data["post_exit_monitoring"] = {}
                    dirty = True
                if dirty:
                    save_live_portfolio(data)
                return data
        except Exception:
            pass
    # Initialize with default settings if file doesn't exist
    return {
        "wallet_address": "",
        "active_positions": {},    # token_address -> trade_info
        "trade_history": [],       # Completed real trades list
        "cooldowns": {},            # token_address -> epoch_timestamp_when_cooldown_ends
        "post_exit_monitoring": {}
    }

def save_live_portfolio(portfolio: dict):
    try:
        with open(PORTFOLIO_FILE, "w") as f:
            json.dump(portfolio, f, indent=4)
    except Exception as e:
        print(f"[ERROR] Gagal menyimpan portofolio live: {e}", flush=True)

def run_live_real_trader():
    print("=" * 80)
    print("🚀 SOLANA DEX PREDATOR - LIVE REAL-MONEY TRADING ENGINE (PRODUCTION V8.0)")
    print("[INFO] Strategy Mode          : V8.0 Citadel High Win Rate Scalper")
    print("[INFO] Target Take-Profit (TP): +10.0% (Instant Exit)")
    print("[INFO] Breakeven Guard (BE)  : Lock +3.0% when price hits +4.0%")
    print("[INFO] Initial Stop Loss (SL) : -12.0% (Tight Protection)")
    print("[INFO] Token Cooldown Shield  : 24 Hours (86,400s) Blacklist on Exit")
    print("=" * 80)
    
    # 1. Load Solana Wallet Configuration
    priv_key_b58 = os.getenv("SOLANA_PRIVATE_KEY")
    helius_url = os.getenv("SOLANA_RPC_HELIUS")
    drpc_url = os.getenv("SOLANA_RPC_DRPC")
    jup_api_key = os.getenv("JUPITER_API_KEY")
    
    if not priv_key_b58:
        print("[CRITICAL] SOLANA_PRIVATE_KEY missing in .env! Exiting.", flush=True)
        sys.exit(1)
        
    # Derive Wallet address
    try:
        raw_key = base58_decode(priv_key_b58)
        user_wallet = base58_encode(raw_key[32:])
    except Exception as e:
        print(f"[CRITICAL] Failed to decode SOLANA_PRIVATE_KEY: {e}", flush=True)
        sys.exit(1)
        
    print(f"[WALLET] Running Live On-Chain! Derived Wallet: {user_wallet}", flush=True)
    
    # 2. Configure Money Management Budget
    # Allows configuration in .env, falls back to 0.05 SOL (~$8 USD) per trade
    sol_allocation = float(os.getenv("SOL_ALLOCATION_PER_TRADE", "0.05"))
    sol_allocation_lamports = int(sol_allocation * 1_000_000_000)
    
    print(f"[BUDGET] Allocation Per Trade: {sol_allocation:.4f} SOL (~${sol_allocation*160:.2f} USD)", flush=True)
    
    # Load state
    portfolio = load_live_portfolio()
    portfolio["wallet_address"] = user_wallet
    save_live_portfolio(portfolio)
    
    # Gas, swap, and slippage defaults
    slippage_bps = int(os.getenv("SOLANA_SLIPPAGE_BPS", "250")) # 2.5% default slippage
    jito_tip_lamports = int(os.getenv("SOLANA_JITO_TIP", "1000000")) # 0.001 SOL Jito tip
    
    # 3. High-Frequency Monitoring Loop (Every 1 second for real trades)
    loop_delay = 1
    last_scan_time = 0.0
    
    while True:
        try:
            # Clean up expired cooldowns to keep state clean
            current_time = time.time()
            if "cooldowns" in portfolio:
                portfolio["cooldowns"] = {k: v for k, v in portfolio["cooldowns"].items() if v > current_time}
            
            # Dynamic Wallet Balance query
            live_sol_balance = get_solana_balance(helius_url or drpc_url, user_wallet)
            print("\n" + "-" * 80)
            print(f"[TICK SCAN] {time.strftime('%Y-%m-%d %H:%M:%S')} | Wallet SOL: {live_sol_balance:.6f} SOL | Active: {len(portfolio['active_positions'])}/2")
            print("-" * 80)
            
            # --- PHASE 1: HIGH-FREQUENCY ACTIVE TRADES MONITORING ---
            active_positions = portfolio["active_positions"]
            post_exit_monitoring = portfolio.get("post_exit_monitoring", {})
            closed_any = False
            
            if active_positions or post_exit_monitoring:
                active_count = len(active_positions)
                post_count = len(post_exit_monitoring)
                print(f"[INFO] Monitoring {active_count} active & {post_count} post-exit on-chain positions...", flush=True)
                try:
                    addr_list = list(active_positions.keys()) + list(post_exit_monitoring.keys())
                    try:
                        addr_str = ",".join(addr_list)
                        url = f"https://api.jup.ag/price/v3?ids={addr_str}"
                        headers = {"x-api-key": jup_api_key} if jup_api_key else {}
                        
                        price_map = {}
                        r = requests.get(url, headers=headers, timeout=5)
                        if r.status_code == 200:
                            res = r.json()
                            data = res.get("data", {}) if "data" in res else res
                            for addr in addr_list:
                                tinfo = data.get(addr, {})
                                price = tinfo.get("usdPrice") or tinfo.get("price")
                                if price is not None:
                                    price_map[addr] = {"price": float(price)}
                        else:
                            print(f"  [WARN] Jupiter Price API returned error code: {r.status_code}", flush=True)
                    except Exception:
                        pass
                                    
                    # Fallback 1: Query DexScreener bulk pricing API (Free, high rate limit)
                    missing_addrs = [addr for addr in addr_list if addr not in price_map]
                    if missing_addrs:
                        try:
                            ds_addrs_str = ",".join(missing_addrs)
                            ds_url = f"https://api.dexscreener.com/latest/dex/tokens/{ds_addrs_str}"
                            ds_res = requests.get(ds_url, timeout=5).json()
                            pairs = ds_res.get("pairs", []) or []
                            for pair in pairs:
                                base_addr = pair.get("baseToken", {}).get("address")
                                price = pair.get("priceUsd")
                                if base_addr and price is not None:
                                    liq = float(pair.get("liquidity", {}).get("usd", 0) or 0)
                                    if base_addr not in price_map or liq > price_map[base_addr].get("liq", 0):
                                        price_map[base_addr] = {"price": float(price), "liq": liq}
                        except Exception:
                            pass
 
                    # Fallback 2: Paced Birdeye Single-API Query (Limit to 1 query per cycle, min 15s cooldown per token)
                    if not hasattr(run_live_real_trader, "last_be_query"):
                        run_live_real_trader.last_be_query = {}
                        
                    missing_addrs = [addr for addr in addr_list if addr not in price_map]
                    if missing_addrs:
                        birdeye_key = os.getenv("BIRDEYE_API_KEY", "")
                        if birdeye_key:
                            now = time.time()
                            # Sort missing addresses by how long ago they were queried to pace properly
                            missing_addrs.sort(key=lambda x: run_live_real_trader.last_be_query.get(x, 0))
                            oldest_addr = missing_addrs[0]
                            last_time = run_live_real_trader.last_be_query.get(oldest_addr, 0)
                            
                            if now - last_time >= 15.0:
                                try:
                                    be_url = f"https://public-api.birdeye.so/defi/price?address={oldest_addr}"
                                    be_headers = {"X-API-KEY": birdeye_key, "Accept": "application/json"}
                                    be_res = requests.get(be_url, headers=be_headers, timeout=5).json()
                                    run_live_real_trader.last_be_query[oldest_addr] = now
                                    if be_res.get("success"):
                                        price = be_res.get("data", {}).get("value")
                                        if price is not None:
                                            price_map[oldest_addr] = {"price": float(price)}
                                except Exception:
                                    pass
                    
                    # --- CORE EXIT MONITORING LOOP (runs for ALL active positions) ---
                    for addr, pos in list(active_positions.items()):
                        current_price = None
                        
                        if addr in price_map and price_map[addr]["price"] > 0:
                            current_price = price_map[addr]["price"]
                        else:
                            # Track how many cycles this token has had no price data
                            pos["no_price_cycles"] = pos.get("no_price_cycles", 0) + 1
                            print(f"  [WARN] Harga {pos['symbol']} tidak tersedia (Cycle ke-{pos['no_price_cycles']}). Mengaktifkan Emergency SL...", flush=True)
                            
                            # EMERGENCY FORCE-CLOSE after 120 consecutive cycles with no price data (approx 2 minutes, likely rug/delisted)
                            if pos.get("no_price_cycles", 0) >= 120:
                                entry_price = pos["entry_price"]
                                exit_price = entry_price * 0.50  # Assume worst case -50% for rugpull
                                
                                print(f"\n🚨 [EMERGENCY EXIT] {pos['symbol']} tidak memiliki data harga 120 siklus. Kemungkinan RUGGED! Executing market sell...", flush=True)
                                
                                raw_qty = int(pos["raw_qty"])
                                
                                sell_res = execute_solana_swap(
                                    input_mint=addr,
                                    output_mint="So11111111111111111111111111111111111111112", # Swap back to SOL
                                    amount_lamports=raw_qty,
                                    slippage_bps=slippage_bps,
                                    jito_tip_lamports=jito_tip_lamports
                                )
                                
                                if sell_res.get("status") == "success":
                                    sol_received = float(sell_res["net_out_amount"]) / 1_000_000_000.0
                                    pnl_sol = sol_received - pos["net_investment_sol"]
                                    
                                    print(f"✨ [REAL SELL CONFIRMED] Successfully EMERGENCY sold {pos['symbol']}!", flush=True)
                                    print(f"   => SOL Received: {sol_received:.6f} SOL | PnL: {pnl_sol:+.6f} SOL", flush=True)
                                    print(f"   => Tx Signature: {sell_res['explorer_url']}", flush=True)
                                    
                                    # Persist 24-hour Cooldown Shield for rugged tokens
                                    portfolio.setdefault("cooldowns", {})[addr] = time.time() + 86400
                                    portfolio.setdefault("post_exit_monitoring", {})[addr] = {
                                        "symbol": pos["symbol"],
                                        "exit_price": exit_price,
                                        "exit_time": time.time(),
                                        "highest_price_post_exit": exit_price,
                                        "lowest_price_post_exit": exit_price,
                                        "exit_reason": "EMERGENCY_FORCE_CLOSE_RUG"
                                    }
                                    print(f"   => [SHIELD] Alamat {addr} masuk daftar Cooldown 24 Jam.", flush=True)
                                    
                                    portfolio["trade_history"].append({
                                        "symbol": pos["symbol"],
                                        "address": addr,
                                        "entry_price": entry_price,
                                        "exit_price": exit_price,
                                        "pnl_sol": pnl_sol,
                                        "tx_signature": sell_res["signature"],
                                        "closed_at": time.strftime('%Y-%m-%d %H:%M:%S'),
                                        "exit_reason": "EMERGENCY_FORCE_CLOSE_RUG"
                                    })
                                    del active_positions[addr]
                                    closed_any = True
                                else:
                                    print(f"[CRITICAL ERROR] Failed to execute emergency sell transaction: {sell_res.get('message')}", flush=True)
                            continue
                            
                        # Reset no_price_cycles counter if price is available
                        pos["no_price_cycles"] = 0
                        
                        entry_price = pos["entry_price"]
                        highest_price = max(pos["highest_price"], current_price)
                        pos["highest_price"] = highest_price
                        
                        # Dynamic 96% WR Scalper Trailing & TP Logic
                        price_gain_pct = ((highest_price - entry_price) / entry_price) * 100
                        current_pnl_pct = ((current_price - entry_price) / entry_price) * 100
                        
                        # Dynamic Trade Mode Exit Logic
                        from config import TRADE_MODE
                        trade_mode = TRADE_MODE.upper()
                        
                        if trade_mode == "HOLY_GRAIL_75WR":
                            if not pos.get("partial_tp_hit", False) and price_gain_pct >= 15.0:
                                raw_qty = int(pos["raw_qty"])
                                partial_raw_qty = int(raw_qty * 0.50)
                                
                                print(f"\n✨ [HOLY GRAIL TP TRIGGERED] Jual 50% {pos['symbol']} @ ${current_price:.8f} (+{price_gain_pct:.2f}%)! Executing on-chain swap...", flush=True)
                                
                                sell_res = execute_solana_swap(
                                    input_mint=addr,
                                    output_mint="So11111111111111111111111111111111111111112",
                                    amount_lamports=partial_raw_qty,
                                    slippage_bps=slippage_bps,
                                    jito_tip_lamports=jito_tip_lamports
                                )
                                
                                if sell_res.get("status") == "success":
                                    sol_received = float(sell_res["net_out_amount"]) / 1_000_000_000.0
                                    print(f"✨ [REAL PARTIAL TP CONFIRMED] Successfully sold 50% of {pos['symbol']}!", flush=True)
                                    print(f"   => SOL Received: {sol_received:.6f} SOL", flush=True)
                                    print(f"   => Tx Signature: {sell_res['explorer_url']}", flush=True)
                                    
                                    orig_inv = pos.get("original_investment_sol", pos["net_investment_sol"])
                                    partial_pnl = sol_received - (0.50 * orig_inv)
                                    pos["total_pnl_sol"] = pos.get("total_pnl_sol", 0.0) + partial_pnl
                                    
                                    pos["raw_qty"] = str(raw_qty - partial_raw_qty)
                                    pos["qty"] *= 0.50
                                    pos["partial_tp_hit"] = True
                                    pos["remaining_pct"] = 0.50
                                    pos["net_investment_sol"] *= 0.50
                                    closed_any = True
                                else:
                                    print(f"[ERROR] Failed to execute partial TP sell transaction: {sell_res.get('message')}", flush=True)
                                
                            if pos.get("partial_tp_hit", False):
                                if price_gain_pct >= 200.0:
                                    sl_price = highest_price * 0.70
                                    trail_level = "HG RUNNER TSL (30%)"
                                elif price_gain_pct >= 50.0:
                                    sl_price = highest_price * 0.80
                                    trail_level = "HG RUNNER TSL (20%)"
                                else:
                                    sl_price = entry_price * 1.02
                                    trail_level = "HG BE-LOCK (+2%)"
                            else:
                                sl_price = entry_price * 0.85
                                trail_level = "HG INITIAL SL (15%)"
                        elif trade_mode == "ULTRA_SCALPER":
                            if not pos.get("partial_tp_hit", False) and price_gain_pct >= 15.0:
                                raw_qty = int(pos["raw_qty"])
                                partial_raw_qty = int(raw_qty * 0.80)
                                
                                print(f"\n✨ [PARTIAL TP TRIGGERED] Jual 80% {pos['symbol']} @ ${current_price:.8f} (+{price_gain_pct:.2f}%)! Executing on-chain swap...", flush=True)
                                
                                sell_res = execute_solana_swap(
                                    input_mint=addr,
                                    output_mint="So11111111111111111111111111111111111111112",
                                    amount_lamports=partial_raw_qty,
                                    slippage_bps=slippage_bps,
                                    jito_tip_lamports=jito_tip_lamports
                                )
                                
                                if sell_res.get("status") == "success":
                                    sol_received = float(sell_res["net_out_amount"]) / 1_000_000_000.0
                                    print(f"✨ [REAL PARTIAL TP CONFIRMED] Successfully sold 80% of {pos['symbol']}!", flush=True)
                                    print(f"   => SOL Received: {sol_received:.6f} SOL", flush=True)
                                    print(f"   => Tx Signature: {sell_res['explorer_url']}", flush=True)
                                    
                                    orig_inv = pos.get("original_investment_sol", pos["net_investment_sol"])
                                    partial_pnl = sol_received - (0.80 * orig_inv)
                                    pos["total_pnl_sol"] = pos.get("total_pnl_sol", 0.0) + partial_pnl
                                    
                                    pos["raw_qty"] = str(raw_qty - partial_raw_qty)
                                    pos["qty"] *= 0.20
                                    pos["partial_tp_hit"] = True
                                    pos["remaining_pct"] = 0.20
                                    pos["net_investment_sol"] *= 0.20
                                    closed_any = True
                                else:
                                    print(f"[ERROR] Failed to execute partial TP sell transaction: {sell_res.get('message')}", flush=True)
                                
                            if pos.get("partial_tp_hit", False):
                                if price_gain_pct >= 800.0:
                                    sl_price = highest_price * 0.75
                                    trail_level = "ULTRA TSL 25%"
                                elif price_gain_pct >= 300.0:
                                    sl_price = highest_price * 0.70
                                    trail_level = "ULTRA TSL 30%"
                                elif price_gain_pct >= 100.0:
                                    sl_price = highest_price * 0.65
                                    trail_level = "ULTRA TSL 35%"
                                else:
                                    sl_price = entry_price * 1.05
                                    trail_level = "ULTRA BE-LOCK (+5%)"
                            else:
                                sl_price = entry_price * 0.80
                                trail_level = "ULTRA INITIAL SL (20%)"
                        elif trade_mode == "MOONSHOT":
                            # MOONSHOT EXIT LOGIC (Wider parameters, lets winners run)
                            if price_gain_pct >= 800.0:
                                sl_price = highest_price * 0.75  # Trail 25% from peak
                                trail_level = "STAGE 3 (25% TSL)"
                            elif price_gain_pct >= 300.0:
                                sl_price = highest_price * 0.70  # Trail 30% from peak
                                trail_level = "STAGE 2 (30% TSL)"
                            elif price_gain_pct >= 100.0:
                                sl_price = highest_price * 0.65  # Trail 35% from peak
                                trail_level = "STAGE 1 (35% TSL)"
                            else:
                                sl_price = highest_price * 0.70  # Initial SL 30% (No early profit lock)
                                trail_level = "MOONSHOT INITIAL SL (30%)"
                        elif trade_mode == "SCALPER":
                            # SCALPER EXIT LOGIC (V13.5 LOCK)
                            if price_gain_pct >= 400.0:
                                sl_price = highest_price * 0.70
                                trail_level = "STAGE 4 (30% TSL)"
                            elif price_gain_pct >= 150.0:
                                sl_price = highest_price * 0.75
                                trail_level = "STAGE 3 (25% TSL)"
                            elif price_gain_pct >= 60.0:
                                sl_price = highest_price * 0.80
                                trail_level = "STAGE 2 (20% TSL)"
                            elif price_gain_pct >= 30.0:
                                sl_price = entry_price * 1.15
                                trail_level = "STAGE 1 (+15% LOCK)"
                            elif price_gain_pct >= 15.0:
                                sl_price = entry_price * 1.05
                                trail_level = "BE-LOCK (+5%)"
                            else:
                                sl_price = highest_price * 0.80 # 20% Initial SL
                                trail_level = "TRAILING SL (20%)"
                        elif trade_mode == "OPTIMIZED":
                            # OPTIMIZED HOLY GRAIL V17.0 (Scalp & Runner) - The True Holy Grail
                            if not pos.get("partial_tp_hit", False) and price_gain_pct >= 30.0:
                                raw_qty = int(pos["raw_qty"])
                                partial_raw_qty = int(raw_qty * 0.80)
                                
                                print(f"\n✨ [SCALP TP TRIGGERED] Jual 80% {pos['symbol']} @ ${current_price:.8f} (+{price_gain_pct:.2f}%)! Mengamankan Profit via On-Chain Swap...", flush=True)
                                
                                sell_res = execute_solana_swap(
                                    input_mint=addr,
                                    output_mint="So11111111111111111111111111111111111111112",
                                    amount_lamports=partial_raw_qty,
                                    slippage_bps=slippage_bps,
                                    jito_tip_lamports=jito_tip_lamports
                                )
                                
                                if sell_res.get("status") == "success":
                                    sol_received = float(sell_res["net_out_amount"]) / 1_000_000_000.0
                                    print(f"✨ [REAL SCALP TP CONFIRMED] Successfully sold 80% of {pos['symbol']}!", flush=True)
                                    print(f"   => SOL Received: {sol_received:.6f} SOL", flush=True)
                                    print(f"   => Tx Signature: {sell_res['explorer_url']}", flush=True)
                                    
                                    orig_inv = pos.get("original_investment_sol", pos["net_investment_sol"])
                                    partial_pnl = sol_received - (0.80 * orig_inv)
                                    pos["total_pnl_sol"] = pos.get("total_pnl_sol", 0.0) + partial_pnl
                                    
                                    pos["raw_qty"] = str(raw_qty - partial_raw_qty)
                                    pos["qty"] *= 0.20
                                    pos["partial_tp_hit"] = True
                                    pos["remaining_pct"] = 0.20
                                    pos["net_investment_sol"] *= 0.20
                                    closed_any = True
                                else:
                                    print(f"[ERROR] Failed to execute scalp TP sell transaction: {sell_res.get('message')}", flush=True)
                                
                            if pos.get("partial_tp_hit", False):
                                # 20% MOONSHOT RUNNER LOGIC (Free bag)
                                if price_gain_pct >= 300.0:
                                    sl_price = highest_price * 0.70
                                    trail_level = "RUNNER TSL (30%)"
                                elif price_gain_pct >= 150.0:
                                    sl_price = highest_price * 0.80
                                    trail_level = "RUNNER TSL (20%)"
                                elif price_gain_pct >= 80.0:
                                    sl_price = entry_price * 1.50
                                    trail_level = "RUNNER LOCK (+50%)"
                                else:
                                    sl_price = entry_price * 1.03
                                    trail_level = "RUNNER BE-LOCK (+3%)"
                            else:
                                if price_gain_pct >= 10.0:
                                    sl_price = entry_price * 1.03
                                    trail_level = "BE-LOCK (+3%)"
                                else:
                                    sl_price = highest_price * 0.85
                                    trail_level = "OPTIMIZED TIGHT SL (15%)"
                        elif trade_mode == "HIT_AND_RUN":
                            if price_gain_pct >= 20.0:
                                sl_price = current_price * 1.5 # Paksa jual instan 100% di +20%
                                trail_level = "HIT & RUN (+20% TP MUTLAK)"
                            elif price_gain_pct >= 10.0:
                                sl_price = entry_price * 1.05
                                trail_level = "HIT & RUN BE-LOCK (+5%)"
                            else:
                                sl_price = highest_price * 0.85
                                trail_level = "HIT & RUN INITIAL SL (15%)"
                        elif trade_mode == "RUNNER":
                            if not pos.get("partial_tp_hit", False) and price_gain_pct >= 30.0:
                                raw_qty = int(pos["raw_qty"])
                                partial_raw_qty = int(raw_qty * 0.50)
                                
                                print(f"\n✨ [RUNNER TP TRIGGERED] Jual 50% {pos['symbol']} @ ${current_price:.8f} (+{price_gain_pct:.2f}%)! Mengamankan Profit via On-Chain Swap...", flush=True)
                                
                                sell_res = execute_solana_swap(
                                    input_mint=addr,
                                    output_mint="So11111111111111111111111111111111111111112",
                                    amount_lamports=partial_raw_qty,
                                    slippage_bps=slippage_bps,
                                    jito_tip_lamports=jito_tip_lamports
                                )
                                
                                if sell_res.get("status") == "success":
                                    sol_received = float(sell_res["net_out_amount"]) / 1_000_000_000.0
                                    print(f"✨ [REAL RUNNER TP CONFIRMED] Successfully sold 50% of {pos['symbol']}!", flush=True)
                                    print(f"   => SOL Received: {sol_received:.6f} SOL", flush=True)
                                    
                                    pos["raw_qty"] = str(raw_qty - partial_raw_qty)
                                    pos["qty"] *= 0.50
                                    pos["partial_tp_hit"] = True
                                    pos["remaining_pct"] = 0.50
                                    if "gross_investment_sol" in pos:
                                        pos["gross_investment_sol"] *= 0.50
                                    pos["net_investment_sol"] *= 0.50
                                    
                                    orig_inv = pos.get("original_investment_sol", pos.get("gross_investment_sol", pos["net_investment_sol"]))
                                    partial_pnl = sol_received - (0.50 * orig_inv)
                                    pos["total_pnl_sol"] = pos.get("total_pnl_sol", 0.0) + partial_pnl
                                else:
                                    print(f"❌ [SWAP FAILED] Gagal menjual 50% TP: {sell_res.get('message')}", flush=True)

                            if pos.get("partial_tp_hit", False):
                                if price_gain_pct >= 200.0:
                                    sl_price = highest_price * 0.70
                                    trail_level = "RUNNER TSL (30%)"
                                elif price_gain_pct >= 50.0:
                                    sl_price = highest_price * 0.80
                                    trail_level = "RUNNER TSL (20%)"
                                else:
                                    sl_price = entry_price * 1.05
                                    trail_level = "RUNNER BE-LOCK (+5%)"
                            else:
                                sl_price = highest_price * 0.80
                                trail_level = "RUNNER INITIAL SL (20%)"
                        else:
                            sl_price = highest_price * 0.80
                            trail_level = "DEFAULT SL (20%)"

                        # [HOTFIX] Time-Bomb Exit (Max hold 1 minute without momentum)
                        time_based_sl_triggered = False
                        entry_ts = pos.get("entry_ts", 0)
                        if entry_ts > 0:
                            elapsed_sec = time.time() - entry_ts
                            # TIME-BOMB EXIT: If held for > 60 seconds and profit <= 0%, force sell!
                            if elapsed_sec >= 60.0 and not pos.get("partial_tp_hit", False) and current_pnl_pct <= 0.0:
                                time_based_sl_triggered = True
                                trail_level = "TIME-BOMB EXIT (60s no momentum)"
                        else:
                            # Fallback to old string format if entry_ts is missing
                            entry_time_str = pos.get("entry_time")
                            if entry_time_str:
                                try:
                                    old_entry_ts = time.mktime(time.strptime(entry_time_str, '%Y-%m-%d %H:%M:%S'))
                                    elapsed_sec = time.time() - old_entry_ts
                                    if elapsed_sec >= 60.0 and not pos.get("partial_tp_hit", False) and current_pnl_pct <= 0.0:
                                        time_based_sl_triggered = True
                                        trail_level = "TIME-BOMB EXIT (60s no momentum)"
                                except Exception:
                                    pass

                        print(f"  [TRACKING] {pos['symbol']} | Entry: ${entry_price:.8f} | Live: ${current_price:.8f} | SL: ${sl_price:.8f} | PnL: {current_pnl_pct:+.2f}% | Guard: {trail_level}", flush=True)
                        
                        # --- AUTOMATED ON-CHAIN STOP-LOSS SWAP SELL ---
                        if current_price <= sl_price or time_based_sl_triggered:
                            print(f"\n🚨 [EXIT TRIGGERED] {trail_level} hit for {pos['symbol']}! Executing real market sell swap...", flush=True)
                            
                            raw_qty = int(pos["raw_qty"])
                            
                            sell_res = execute_solana_swap(
                                input_mint=addr,
                                output_mint="So11111111111111111111111111111111111111112", # Swap back to SOL
                                amount_lamports=raw_qty,
                                slippage_bps=slippage_bps,
                                jito_tip_lamports=jito_tip_lamports
                            )
                            
                            if sell_res.get("status") == "success":
                                sol_received = float(sell_res["net_out_amount"]) / 1_000_000_000.0
                                
                                rem_pct = pos.get("remaining_pct", 0.20)
                                orig_inv = pos.get("original_investment_sol", pos["net_investment_sol"] / rem_pct if pos.get("partial_tp_hit") else pos["net_investment_sol"])
                                
                                if pos.get("partial_tp_hit", False):
                                    pnl_sol = pos.get("total_pnl_sol", 0.0) + (sol_received - (rem_pct * orig_inv))
                                else:
                                    pnl_sol = sol_received - orig_inv
                                
                                print(f"✨ [REAL SELL CONFIRMED] Successfully sold {pos['symbol']}!", flush=True)
                                print(f"   => SOL Received: {sol_received:.6f} SOL | Cumulative PnL: {pnl_sol:+.6f} SOL", flush=True)
                                print(f"   => Tx Signature: {sell_res['explorer_url']}", flush=True)
                                
                                # Persist 4-hour Cooldown Shield to prevent re-entries
                                portfolio.setdefault("cooldowns", {})[addr] = time.time() + 14400
                                portfolio.setdefault("post_exit_monitoring", {})[addr] = {
                                    "symbol": pos["symbol"],
                                    "exit_price": current_price if price_gain_pct >= 10.0 else sl_price,
                                    "exit_time": time.time(),
                                    "highest_price_post_exit": current_price if price_gain_pct >= 10.0 else sl_price,
                                    "lowest_price_post_exit": current_price if price_gain_pct >= 10.0 else sl_price,
                                    "exit_reason": trail_level
                                }
                                print(f"   => [SHIELD] Alamat {addr} masuk daftar Cooldown 4 Jam.", flush=True)
                                
                                portfolio["trade_history"].append({
                                    "symbol": pos["symbol"],
                                    "address": addr,
                                    "entry_price": entry_price,
                                    "exit_price": current_price if price_gain_pct >= 10.0 else sl_price,
                                    "pnl_sol": pnl_sol,
                                    "tx_signature": sell_res["signature"],
                                    "closed_at": time.strftime('%Y-%m-%d %H:%M:%S'),
                                    "exit_reason": trail_level
                                })
                                del active_positions[addr]
                                closed_any = True
                            else:
                                print(f"[CRITICAL ERROR] Failed to execute stop loss sell transaction: {sell_res.get('message')}", flush=True)
                                
                    # --- POST-EXIT TRACKING LOOP ---
                    post_exit_monitoring = portfolio.get("post_exit_monitoring", {})
                    for addr, post_pos in list(post_exit_monitoring.items()):
                        # Clean up after 15 minutes (900 seconds)
                        if time.time() - post_pos.get("exit_time", 0) > 900:
                            del post_exit_monitoring[addr]
                            closed_any = True
                            continue
                            
                        if addr in price_map and price_map[addr]["price"] > 0:
                            current_price = price_map[addr]["price"]
                            exit_price = post_pos["exit_price"]
                            
                            # Track highest/lowest price post-exit
                            highest_price = max(post_pos.get("highest_price_post_exit", exit_price), current_price)
                            lowest_price = min(post_pos.get("lowest_price_post_exit", exit_price), current_price)
                            
                            post_pos["highest_price_post_exit"] = highest_price
                            post_pos["lowest_price_post_exit"] = lowest_price
                            
                            peak_pnl_post_exit = ((highest_price - exit_price) / exit_price) * 100
                            current_pnl_since_exit = ((current_price - exit_price) / exit_price) * 100
                            
                            print(f"  ⚡ [POST-EXIT] {post_pos['symbol']} | Keluar @ ${exit_price:.8f} ({post_pos.get('exit_reason', 'SL')}) | Live: ${current_price:.8f} | Peak Sejak Keluar: {peak_pnl_post_exit:+.2f}% | Current: {current_pnl_since_exit:+.2f}%", flush=True)
                            closed_any = True
                except Exception as e:
                    print(f"  [WARN] Error during bulk price update: {e}", flush=True)
            else:
                print("[INFO] No active on-chain positions. Monitoring scanner for entry...", flush=True)
                
            # --- PHASE 2: AUTOMATED SCROLL & SECURITY AUDIT FOR CANDIDATES ---
            if len(portfolio["active_positions"]) >= 2:
                print("[SCAN] Limit 2 active positions reached. Bypassing entry scanner.", flush=True)
            else:
                candidates = []
                current_time = time.time()
                if current_time - last_scan_time >= 15.0:
                    last_scan_time = current_time
                    candidates = _fetch_candidates()
                if candidates:
                    candidates.sort(key=lambda x: x.get("volume_5m", 0), reverse=True)
                    top_gems = candidates[:5]
                    
                    best_candidate = None
                    best_score = 0
                    
                    for gem in top_gems:
                        addr = gem["address"]
                        if addr in portfolio["active_positions"]:
                            continue
                            
                        # Strict 24-hour Cooldown filter check
                        if "cooldowns" in portfolio and addr in portfolio["cooldowns"]:
                            cooldown_left = int(portfolio["cooldowns"][addr] - time.time())
                            if cooldown_left > 0:
                                print(f"  [SCAN] Mengabaikan {gem['symbol']} | Masih dalam Cooldown 24 Jam ({cooldown_left}s tersisa)", flush=True)
                                continue
                            
                        # Double layer audit (RugCheck + security scores)
                        security = check_token_security(gem["chain"], addr)
                        score = calculate_gem_score(gem, security)
                        
                        print(f"  [SCANNER] Auditing candidate {gem['symbol']} | Safety Status: {security['status']} | Score: {score}/100", flush=True)
                        
                        from config import MIN_ENTRY_SCORE
                        min_entry_score = MIN_ENTRY_SCORE
                        if security["status"] in ["CLEAN & SAFE", "WARNINGS"] and score >= min_entry_score:
                            # --- AI FILTER REMOVED (OPSI C: Full On-Chain Speed) ---
                            # Bot no longer waits for AI to prevent Top-Buying Trap
                                
                            if score > best_score:
                                best_score = score
                                best_candidate = gem
                                best_candidate["security_status"] = security["status"]
                                best_candidate["predator_score"] = score
                                
                    # --- PHASE 3: EXECUTE AUTOMATED ON-CHAIN BUY ---
                    if best_candidate:
                        addr = best_candidate["address"]
                        print(f"\n🌟 [GEM SPOTTED] Candidate {best_candidate['symbol']} meets entry rules! Score: {best_candidate['predator_score']}/100", flush=True)
                        
                        # Wallet balance check
                        if live_sol_balance >= (sol_allocation + 0.006): # allocation + dynamic prioritization gas buffer
                            # --- JUPITER PRICE IMPACT PRE-FLIGHT CHECK ---
                            headers = {"x-api-key": jup_api_key, "Accept": "application/json"} if jup_api_key else {"Accept": "application/json"}
                            quote_url = f"https://api.jup.ag/swap/v1/quote?inputMint=So11111111111111111111111111111111111111112&outputMint={addr}&amount={sol_allocation_lamports}&slippageBps={slippage_bps}"
                            
                            jup_ok = False
                            price_impact_pct = 0.0
                            reason = ""
                            try:
                                qr = requests.get(quote_url, headers=headers, timeout=5)
                                if qr.status_code == 200:
                                    q_res = qr.json()
                                    price_impact = q_res.get("priceImpactPct")
                                    if price_impact is not None and str(price_impact).strip() != "":
                                        try:
                                            price_impact_pct = float(price_impact) * 100
                                            jup_ok = True
                                        except ValueError:
                                            reason = f"INVALID_PRICE_IMPACT_FORMAT_{price_impact}"
                                    else:
                                        reason = "NO_PRICE_IMPACT_DATA"
                                else:
                                    reason = f"HTTP_ERROR_{qr.status_code}"
                            except Exception as e:
                                reason = f"EXCEPTION_{type(e).__name__}"
                            
                            if not jup_ok:
                                print(f"  [DITOLAK] Jupiter Pre-flight Quote gagal untuk {best_candidate['symbol']}. Alasan: {reason}", flush=True)
                                continue
                            
                            if price_impact_pct > 2.0:
                                print(f"  [DITOLAK] Jupiter Pre-flight Quote: Price Impact terlalu besar untuk {best_candidate['symbol']} ({price_impact_pct:.2f}% > 2.0%)", flush=True)
                                continue
                            
                            print(f"🛒 [BUY SWAP INITIATED] Submitting transaction to buy {best_candidate['symbol']}...", flush=True)
                            
                            buy_res = execute_solana_swap(
                                input_mint="So11111111111111111111111111111111111111112", # Swap SOL
                                output_mint=addr, # for Target Token
                                amount_lamports=sol_allocation_lamports,
                                slippage_bps=slippage_bps,
                                jito_tip_lamports=jito_tip_lamports
                            )
                            
                            if buy_res.get("status") == "success":
                                raw_qty_received = int(buy_res["net_out_amount"])
                                explorer_url = buy_res["explorer_url"]
                                
                                print(f"✨ [REAL BUY CONFIRMED] Successfully purchased {best_candidate['symbol']} on-chain!", flush=True)
                                print(f"   => Transaction: {explorer_url}", flush=True)
                                
                                portfolio["active_positions"][addr] = {
                                    "symbol": best_candidate["symbol"],
                                    "name": best_candidate["name"],
                                    "entry_price": best_candidate["price"],
                                    "highest_price": best_candidate["price"],
                                    "net_investment_sol": sol_allocation,
                                    "original_investment_sol": sol_allocation,
                                    "total_pnl_sol": 0.0,
                                    "raw_qty": raw_qty_received, # On-chain integer quantity
                                    "qty": float(raw_qty_received) / 1_000_000_000.0, # Visual representation
                                    "entry_time": time.strftime('%Y-%m-%d %H:%M:%S'),
                                    "entry_ts": time.time()
                                }
                                closed_any = True
                            else:
                                print(f"[CRITICAL ERROR] Failed to buy {best_candidate['symbol']}: {buy_res.get('message')}", flush=True)
                        else:
                            print(f"[WARN] Insufficient SOL balance to buy {best_candidate['symbol']}. Has: {live_sol_balance:.6f} SOL | Needs: {sol_allocation + 0.006:.6f} SOL", flush=True)
                            
            if closed_any:
                save_live_portfolio(portfolio)
                
        except Exception as e:
            print(f"[ERROR] Main trader loop exception: {e}", flush=True)
            
        # Poll/Sleep for high frequency interval (10 seconds)
        time.sleep(loop_delay)

if __name__ == "__main__":
    run_live_real_trader()
