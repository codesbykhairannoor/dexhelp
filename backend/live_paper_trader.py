import os
import sys
import time
import json
import requests
from dotenv import load_dotenv

load_dotenv()

# Fix module imports when executed from external cwd (like PM2)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from dex_hunter import _fetch_candidates, check_token_security, calculate_gem_score

# Fix Windows terminal encoding for Emojis
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Production Stability Fix: Dynamic Absolute Path Resolution
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PORTFOLIO_FILE = os.path.join(CURRENT_DIR, "paper_portfolio.json")

def load_portfolio() -> dict:
    default_portfolio = {
        "wallet_balance": 1000.00,
        "initial_capital": 1000.00,
        "active_positions": {},    # token_address -> trade_info
        "trade_history": [],       # List of completed simulated trades
        "cooldowns": {},            # token_address -> epoch_timestamp_when_cooldown_ends
        "post_exit_monitoring": {}
    }
    
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r") as f:
                data = json.load(f)
                
                # --- AUTO-MIGRATION & REPAIR SHIELD ---
                dirty = False
                if "cooldowns" not in data:
                    data["cooldowns"] = {}
                    dirty = True
                if "post_exit_monitoring" not in data:
                    data["post_exit_monitoring"] = {}
                    dirty = True
                if "initial_capital" not in data:
                    data["initial_capital"] = data.get("wallet_balance", 1000.00)
                    dirty = True
                if "active_positions" not in data:
                    data["active_positions"] = {}
                    dirty = True
                if "trade_history" not in data:
                    data["trade_history"] = []
                    dirty = True
                    
                # Fix old active positions format dynamically
                for addr, pos in data["active_positions"].items():
                    if "gross_investment" not in pos:
                        pos["gross_investment"] = pos.get("net_investment", 10.00)
                        dirty = True
                        
                if dirty:
                    with open(PORTFOLIO_FILE, "w") as fw:
                        json.dump(data, fw, indent=4)
                        
                return data
        except Exception:
            pass
            
    # Save default if not existing
    try:
        with open(PORTFOLIO_FILE, "w") as f:
            json.dump(default_portfolio, f, indent=4)
    except Exception:
        pass
    return default_portfolio

def save_portfolio(portfolio: dict):
    try:
        with open(PORTFOLIO_FILE, "w") as f:
            json.dump(portfolio, f, indent=4)
    except Exception as e:
        print(f"[ERROR] Gagal menyimpan portofolio: {e}")

def run_live_paper_trader():
    if "--reset" in sys.argv:
        default_portfolio = {
            "wallet_balance": 1000.00,
            "initial_capital": 1000.00,
            "active_positions": {},
            "trade_history": [],
            "cooldowns": {}
        }
        try:
            with open(PORTFOLIO_FILE, "w") as f:
                json.dump(default_portfolio, f, indent=4)
            print("[RESET] Portofolio dan riwayat trading berhasil di-reset ke modal awal $1,000.00!")
        except Exception as e:
            print(f"[ERROR] Gagal mereset portofolio: {e}")
        return

    portfolio = load_portfolio()
    
    print("=" * 80)
    print("[SYSTEM] SOLANA DEX PREDATOR - LIVE PAPER TRADING ENGINE (V11.0 HIGH-FREQ)")
    print(f"[INFO] Virtual Wallet Balance : ${portfolio['wallet_balance']:.2f}")
    print("[INFO] Max Active Trades      : 10 Concurrent Positions Limit")
    print("[INFO] Target Take-Profit (TP): +30.0% (Let winners run)")
    print("[INFO] BE-Guard               : ACTIVE - Lock +3% when hit +4%")
    print("[INFO] Initial Stop Loss (SL) : -20.0% from peak (Trailing)")
    print("[INFO] Cooldown Shield        : 4 Hours (14,400s) per token")
    print("[INFO] Scan Cycle             : Every 5 seconds (High-Frequency)")
    print("="* 80)
    
    # Costs per trade (Gas + Swap fee + Slippage) - Aligned with real Solana AMM metrics for $10 size
    gas_fee = 0.01          # Real Solana priority fee is ~$0.008 USD
    swap_fee_pct = 0.0025   # Raydium Standard Pool Fee is 0.25%
    slippage_pct = 0.005    # Actual slippage for $10 order in $20k pool is < 0.5%
    
    last_scan_time = 0.0
    while True:
        try:
            print("\n" + "-" * 80)
            print(f"[SCAN CYCLE] {time.strftime('%Y-%m-%d %H:%M:%S')} | Mengaudit pasar live...")
            print("-" * 80)
            
            # Refresh portfolio parameters dynamically without losing trade history
            portfolio = load_portfolio()
            
            # Clean up expired cooldowns to keep state small & clean
            current_time = time.time()
            if "cooldowns" in portfolio:
                portfolio["cooldowns"] = {k: v for k, v in portfolio["cooldowns"].items() if v > current_time}
            
            # --- PHASE 1: UPDATE LIVE ACTIVE POSITIONS ---
            active_positions = portfolio["active_positions"]
            post_exit_monitoring = portfolio.get("post_exit_monitoring", {})
            closed_any = False
            
            if active_positions or post_exit_monitoring:
                active_count = len(active_positions)
                post_count = len(post_exit_monitoring)
                print(f"[INFO] Memantau {active_count} posisi aktif & {post_count} koin pasca-exit secara live...")
                try:
                    # Load JUPITER_API_KEY from .env
                    jupiter_key = os.getenv("JUPITER_API_KEY", "jup_0872d0ca9886efca00560439b283c2bc25821ab36727457792ce61ca352c2f60")
                    if not os.getenv("JUPITER_API_KEY"):
                        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
                        if os.path.exists(env_path):
                            with open(env_path, "r") as ef:
                                for line in ef:
                                    if "JUPITER_API_KEY" in line and "=" in line:
                                        jupiter_key = line.split("=")[-1].strip().strip('"').strip("'")
                                        break

                    # Bulk API Query to prevent rate limiting (429) via Jupiter Premium V3
                    addr_list = list(active_positions.keys()) + list(post_exit_monitoring.keys())
                    addr_str = ",".join(addr_list)
                    url = f"https://api.jup.ag/price/v3?ids={addr_str}"
                    headers = {
                        "x-api-key": jupiter_key,
                        "Accept": "application/json"
                    }
                    
                    price_map = {}
                    try:
                        r = requests.get(url, headers=headers, timeout=5)
                        if r.status_code == 200:
                            res = r.json()
                            data = res.get("data", {}) if "data" in res else res
                            for addr in addr_list:
                                tinfo = data.get(addr, {})
                                price = tinfo.get("usdPrice") or tinfo.get("price")
                                if price is not None:
                                    price_map[addr] = {"price": float(price)}
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
                    if not hasattr(run_live_paper_trader, "last_be_query"):
                        run_live_paper_trader.last_be_query = {}
                        
                    missing_addrs = [addr for addr in addr_list if addr not in price_map]
                    if missing_addrs:
                        birdeye_key = os.getenv("BIRDEYE_API_KEY", "")
                        if birdeye_key:
                            now = time.time()
                            # Sort missing addresses by how long ago they were queried to pace properly
                            missing_addrs.sort(key=lambda x: run_live_paper_trader.last_be_query.get(x, 0))
                            oldest_addr = missing_addrs[0]
                            last_time = run_live_paper_trader.last_be_query.get(oldest_addr, 0)
                            
                            if now - last_time >= 15.0:
                                try:
                                    be_url = f"https://public-api.birdeye.so/defi/price?address={oldest_addr}"
                                    be_headers = {"X-API-KEY": birdeye_key, "Accept": "application/json"}
                                    be_res = requests.get(be_url, headers=be_headers, timeout=5).json()
                                    run_live_paper_trader.last_be_query[oldest_addr] = now
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
                            print(f"  [WARN] Harga {pos['symbol']} tidak tersedia (Cycle ke-{pos['no_price_cycles']}). Mengaktifkan Emergency SL...")
                            
                            # EMERGENCY FORCE-CLOSE after 120 consecutive cycles with no price data (approx 2 minutes, likely rug/delisted)
                            if pos.get("no_price_cycles", 0) >= 120:
                                entry_price = pos["entry_price"]
                                exit_price = entry_price * 0.50  # Assume worst case -50% for rugpull
                                gross_inv = pos.get("gross_investment", pos["net_investment"])
                                pnl_usd = (pos["qty"] * exit_price) - gross_inv
                                realized_pnl_pct = (pnl_usd / gross_inv) * 100
                                
                                print(f"  [EMERGENCY EXIT] {pos['symbol']} tidak memiliki data harga 120 siklus berturut-turut. Kemungkinan RUGGED!")
                                print(f"     => Harga Jual Estimasi: ${exit_price:.8f} | Realized PnL: {realized_pnl_pct:+.2f}% (${pnl_usd:+.2f})")
                                
                                portfolio.setdefault("cooldowns", {})[addr] = time.time() + 86400  # 24 hour cooldown for rugged tokens
                                portfolio.setdefault("post_exit_monitoring", {})[addr] = {
                                    "symbol": pos["symbol"],
                                    "exit_price": exit_price,
                                    "exit_time": time.time(),
                                    "highest_price_post_exit": exit_price,
                                    "lowest_price_post_exit": exit_price,
                                    "exit_reason": "EMERGENCY_FORCE_CLOSE_RUG"
                                }
                                portfolio["wallet_balance"] += pos["qty"] * exit_price
                                portfolio["trade_history"].append({
                                    "symbol": pos["symbol"],
                                    "address": addr,
                                    "entry_price": entry_price,
                                    "exit_price": exit_price,
                                    "pnl_pct": realized_pnl_pct,
                                    "pnl_usd": pnl_usd,
                                    "closed_at": time.strftime('%Y-%m-%d %H:%M:%S'),
                                    "exit_reason": "EMERGENCY_FORCE_CLOSE_RUG"
                                })
                                del active_positions[addr]
                                closed_any = True
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
                                partial_qty = pos["qty"] * 0.50
                                partial_val = partial_qty * current_price
                                portfolio["wallet_balance"] += partial_val
                                print(f"\n✨ [HOLY GRAIL TP] Mengamankan 50% Profit {pos['symbol']} @ ${current_price:.8f} (+{price_gain_pct:.2f}%)!", flush=True)
                                
                                orig_gross = pos.get("original_gross_investment", pos.get("gross_investment", pos["net_investment"]))
                                partial_pnl = partial_val - (0.50 * orig_gross)
                                pos["total_pnl_usd"] = pos.get("total_pnl_usd", 0.0) + partial_pnl
                                
                                pos["qty"] *= 0.50
                                pos["partial_tp_hit"] = True
                                pos["remaining_pct"] = 0.50
                                if "gross_investment" in pos:
                                    pos["gross_investment"] *= 0.50
                                pos["net_investment"] *= 0.50
                                closed_any = True
                                
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
                                partial_qty = pos["qty"] * 0.80
                                partial_val = partial_qty * current_price
                                portfolio["wallet_balance"] += partial_val
                                print(f"\n✨ [PARTIAL TP] Jual 80% {pos['symbol']} @ ${current_price:.8f} (+{price_gain_pct:.2f}%)!", flush=True)
                                
                                # Track partial PnL
                                orig_gross = pos.get("original_gross_investment", pos.get("gross_investment", pos["net_investment"]))
                                partial_pnl = partial_val - (0.80 * orig_gross)
                                pos["total_pnl_usd"] = pos.get("total_pnl_usd", 0.0) + partial_pnl
                                
                                pos["qty"] *= 0.20
                                pos["partial_tp_hit"] = True
                                pos["remaining_pct"] = 0.20
                                if "gross_investment" in pos:
                                    pos["gross_investment"] *= 0.20
                                pos["net_investment"] *= 0.20
                                closed_any = True
                                
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
                                partial_qty = pos["qty"] * 0.80
                                partial_val = partial_qty * current_price
                                portfolio["wallet_balance"] += partial_val
                                print(f"\n✨ [SCALP TP] Jual 80% {pos['symbol']} @ ${current_price:.8f} (+{price_gain_pct:.2f}%)! Mengunci Modal & Profit.", flush=True)
                                
                                orig_gross = pos.get("original_gross_investment", pos.get("gross_investment", pos["net_investment"]))
                                partial_pnl = partial_val - (0.80 * orig_gross)
                                pos["total_pnl_usd"] = pos.get("total_pnl_usd", 0.0) + partial_pnl
                                
                                pos["qty"] *= 0.20
                                pos["partial_tp_hit"] = True
                                pos["remaining_pct"] = 0.20
                                if "gross_investment" in pos:
                                    pos["gross_investment"] *= 0.20
                                pos["net_investment"] *= 0.20
                                closed_any = True
                                
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
                        elif trade_mode == "RUNNER":
                            if not pos.get("partial_tp_hit", False) and price_gain_pct >= 30.0:
                                partial_qty = pos["qty"] * 0.50
                                partial_val = partial_qty * current_price
                                portfolio["wallet_balance"] += partial_val
                                print(f"\n✨ [RUNNER TP] Mengamankan 50% Profit {pos['symbol']} @ ${current_price:.8f} (+{price_gain_pct:.2f}%)!", flush=True)
                                
                                orig_gross = pos.get("original_gross_investment", pos.get("gross_investment", pos["net_investment"]))
                                partial_pnl = partial_val - (0.50 * orig_gross)
                                pos["total_pnl_usd"] = pos.get("total_pnl_usd", 0.0) + partial_pnl
                                
                                pos["qty"] *= 0.50
                                pos["partial_tp_hit"] = True
                                pos["remaining_pct"] = 0.50
                                if "gross_investment" in pos:
                                    pos["gross_investment"] *= 0.50
                                pos["net_investment"] *= 0.50
                                closed_any = True
                                
                            if pos.get("partial_tp_hit", False):
                                if price_gain_pct >= 200.0:
                                    sl_price = highest_price * 0.70
                                    trail_level = "RUNNER TSL (30%)"
                                else:
                                    sl_price = entry_price * 1.05
                                    trail_level = "RUNNER BE-LOCK (+5%)"
                            else:
                                sl_price = highest_price * 0.80
                                trail_level = "RUNNER INITIAL SL (20%)"
                        else:
                            sl_price = highest_price * 0.80
                            trail_level = "DEFAULT SL (20%)"
                            
                        print(f"  [POSITION] {pos['symbol']} | Entry: ${entry_price:.8f} | Live: ${current_price:.8f} | Puncak: ${highest_price:.8f} | SL: ${sl_price:.8f} | PnL: {current_pnl_pct:+.2f}% | Guard: {trail_level}")
                        
                        # [HOTFIX] Time-Based Dead Token Exit (Max hold 25 minutes without taking profit)
                        import time
                        time_based_sl_triggered = False
                        entry_time_str = pos.get("entry_time")
                        if entry_time_str:
                            try:
                                entry_ts = time.mktime(time.strptime(entry_time_str, '%Y-%m-%d %H:%M:%S'))
                                elapsed_mins = (time.time() - entry_ts) / 60.0
                                if elapsed_mins >= 25.0 and not pos.get("partial_tp_hit", False):
                                    time_based_sl_triggered = True
                                    trail_level = "DEAD TOKEN TIMEOUT (25m)"
                            except Exception:
                                pass
                        
                        # Trigger exit ONLY when current price falls below dynamic trailing SL or time limit is reached
                        if current_price <= sl_price or time_based_sl_triggered:
                            exit_price = current_price
                            net_exit_value = pos["qty"] * exit_price
                            
                            rem_pct = pos.get("remaining_pct", 0.20)
                            orig_gross = pos.get("original_gross_investment", pos.get("gross_investment", pos["net_investment"]) / rem_pct if pos.get("partial_tp_hit") else pos.get("gross_investment", pos["net_investment"]))
                            
                            if pos.get("partial_tp_hit", False):
                                total_pnl_usd = pos.get("total_pnl_usd", 0.0) + (net_exit_value - (rem_pct * orig_gross))
                                realized_pnl_pct = (total_pnl_usd / orig_gross) * 100
                                pnl_usd = total_pnl_usd
                            else:
                                pnl_usd = net_exit_value - orig_gross
                                realized_pnl_pct = (pnl_usd / orig_gross) * 100
                            
                            print(f"  [EXIT TRIGGERED] {trail_level} Terpicu untuk {pos['symbol']}!")
                            print(f"     => Harga Jual: ${exit_price:.8f} | Realized PnL: {realized_pnl_pct:+.2f}% (${pnl_usd:+.2f})")
                            
                            portfolio.setdefault("cooldowns", {})[addr] = time.time() + 14400  # 4 Hour cooldown
                            portfolio.setdefault("post_exit_monitoring", {})[addr] = {
                                "symbol": pos["symbol"],
                                "exit_price": exit_price,
                                "exit_time": time.time(),
                                "highest_price_post_exit": exit_price,
                                "lowest_price_post_exit": exit_price,
                                "exit_reason": trail_level
                            }
                            print(f"     => [SHIELD] Alamat {addr} masuk daftar Cooldown 4 Jam.")
                            
                            portfolio["wallet_balance"] += net_exit_value
                            portfolio["trade_history"].append({
                                "symbol": pos["symbol"],
                                "address": addr,
                                "entry_price": entry_price,
                                "exit_price": exit_price,
                                "pnl_pct": realized_pnl_pct,
                                "pnl_usd": pnl_usd,
                                "highest_price_reached": highest_price,
                                "sl_trigger_price": sl_price,
                                "closed_at": time.strftime('%Y-%m-%d %H:%M:%S'),
                                "exit_reason": trail_level
                            })
                            del active_positions[addr]
                            closed_any = True
                            
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
                            
                            print(f"  ⚡ [POST-EXIT] {post_pos['symbol']} | Keluar @ ${exit_price:.8f} ({post_pos.get('exit_reason', 'SL')}) | Live: ${current_price:.8f} | Peak Sejak Keluar: {peak_pnl_post_exit:+.2f}% | Current: {current_pnl_since_exit:+.2f}%")
                            closed_any = True
                except Exception as e:
                    print(f"  [WARN] Gagal melakukan bulk update harga: {e}")
            else:
                print("[INFO] Portofolio Posisi Aktif: KOSONG.")
                
            # --- PHASE 2: SCAN FOR NEW PREMIUM OPPORTUNITIES ---
            # Strict limit check: Max 10 active trades
            if len(active_positions) >= 10:
                print(f"[SCAN] Limit 10 posisi aktif terisi ({len(active_positions)}/10). Mengabaikan scan koin baru.")
            else:
                candidates = []
                current_time = time.time()
                if current_time - last_scan_time >= 15.0:
                    last_scan_time = current_time
                    candidates = _fetch_candidates()
                if candidates:
                    candidates.sort(key=lambda x: x.get("volume_5m", 0), reverse=True)
                    
                    for gem in candidates:
                        if len(active_positions) >= 10:
                            break
                            
                        addr = gem["address"]
                        if addr in active_positions:
                            continue
                            
                        if "cooldowns" in portfolio and addr in portfolio["cooldowns"]:
                            continue
                            
                        security = check_token_security(gem["chain"], addr)
                        score = calculate_gem_score(gem, security)
                        
                        print(f"  [SCAN] {gem['symbol']} | Safety: {security['status']} | Score: {score}/100 | Age: {gem.get('age_estimate_sec',0)//60}m")
                        
                        from config import MIN_ENTRY_SCORE
                        min_entry_score = MIN_ENTRY_SCORE
                        if security["status"] in ["CLEAN & SAFE", "WARNINGS"] and score >= min_entry_score:
                            # --- DEEPSEEK MEMETIC AI FILTER (Final Boss) ---
                            try:
                                from deepseek_ai import evaluate_token
                                print(f"  [AI] Mengirim {gem['symbol']} ke DeepSeek untuk diuji Vibe/Memetic...")
                                memetic_res = evaluate_token(gem['symbol'], gem['name'])
                                if "error" in memetic_res:
                                    print(f"    -> [AI ERROR] Gagal menghubungi DeepSeek. Skip filter memetic. Error: {memetic_res['error']}")
                                else:
                                    memetic_score = memetic_res.get("score", 0)
                                    reason = memetic_res.get("reason", "")
                                    print(f"    -> [DEEPSEEK] Memetic Score: {memetic_score}/100 | {reason}")
                                    if memetic_score < 40:
                                        print(f"    -> [DITOLAK] Memetic AI Score terlalu rendah (<40). Potensi viral kecil.")
                                        continue
                            except Exception as e:
                                print(f"    -> [AI ERROR] DeepSeek tidak tersedia: {e}")
                                
                            # Fixed sizing: $10.00 flat margin per trade
                            trade_allocation = 10.00
                            
                            if portfolio["wallet_balance"] >= trade_allocation:
                                # --- JUPITER PRICE IMPACT PRE-FLIGHT CHECK ---
                                jup_api_key = os.getenv("JUPITER_API_KEY", "")
                                headers = {"x-api-key": jup_api_key, "Accept": "application/json"} if jup_api_key else {"Accept": "application/json"}
                                
                                sol_price = 160.0
                                try:
                                    sol_price_r = requests.get("https://api.jup.ag/price/v3?ids=So11111111111111111111111111111111111111112", headers=headers, timeout=3)
                                    if sol_price_r.status_code == 200:
                                        sol_data = sol_price_r.json().get("data", {})
                                        sol_price = float(sol_data.get("So11111111111111111111111111111111111111112", {}).get("price", 160.0))
                                except Exception:
                                    pass
                                
                                sol_amount = trade_allocation / sol_price
                                amount_lamports = int(sol_amount * 1_000_000_000)
                                quote_url = f"https://api.jup.ag/swap/v1/quote?inputMint=So11111111111111111111111111111111111111112&outputMint={addr}&amount={amount_lamports}&slippageBps=250"
                                
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
                                    print(f"  [DITOLAK] Jupiter Pre-flight Quote gagal untuk {gem['symbol']}. Alasan: {reason}")
                                    continue
                                
                                if price_impact_pct > 2.0:
                                    print(f"  [DITOLAK] Jupiter Pre-flight Quote: Price Impact terlalu besar untuk {gem['symbol']} ({price_impact_pct:.2f}% > 2.0%)")
                                    continue
                                
                                cost_per_trade = gas_fee + (trade_allocation * swap_fee_pct) + (trade_allocation * slippage_pct)
                                net_investment = trade_allocation - cost_per_trade
                                
                                # Aligned with standard AMM math
                                qty = net_investment / gem["price"]
                                
                                # Add new position
                                active_positions[addr] = {
                                    "symbol": gem["symbol"],
                                    "name": gem["name"],
                                    "entry_price": gem["price"],
                                    "highest_price": gem["price"],
                                    "gross_investment": trade_allocation,
                                    "net_investment": net_investment,
                                    "original_gross_investment": trade_allocation,
                                    "total_pnl_usd": 0.0,
                                    "qty": qty,
                                    "entry_time": time.strftime('%Y-%m-%d %H:%M:%S')
                                }
                                
                                portfolio["wallet_balance"] -= trade_allocation
                                closed_any = True
                                
                                print(f"\n[BUY EXECUTED] Membeli {gem['symbol']}!")
                                print(f"   => Harga Entry: ${gem['price']:.8f} | Alokasi: ${trade_allocation:.2f} (Net: ${net_investment:.2f})")
                                print(f"   => Score: {score}/100 | Initial SL: ${gem['price']*(1-0.12):.8f}")
                            else:
                                print(f"\n[SCAN] Dana tidak cukup untuk membeli {gem['symbol']}. Saldo: ${portfolio['wallet_balance']:.2f}")
            
            if closed_any:
                save_portfolio(portfolio)
                print(f"\n[PORTFOLIO] Portofolio Diperbarui! Total Saldo Dompet Virtual: ${portfolio['wallet_balance']:.2f}")
                
        except Exception as e:
            print(f"[ERROR] Loop error: {e}")
            
        # High-frequency refresh every 1 second
        time.sleep(1)

if __name__ == "__main__":
    run_live_paper_trader()
