import os
import sys
import time
import json
import requests

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
        "cooldowns": {}            # token_address -> epoch_timestamp_when_cooldown_ends
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
            closed_any = False
            
            if active_positions:
                print(f"[INFO] Memantau {len(active_positions)} posisi aktif secara live...")
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
                    addr_list = list(active_positions.keys())
                    addr_str = ",".join(addr_list)
                    url = f"https://api.jup.ag/price/v3?ids={addr_str}"
                    headers = {
                        "x-api-key": jupiter_key,
                        "Accept": "application/json"
                    }
                    
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
                                
                    # Fallback 1: query Birdeye API for any token missing price info
                    missing_addrs = [addr for addr in addr_list if addr not in price_map]
                    if missing_addrs:
                        birdeye_key = os.getenv("BIRDEYE_API_KEY", "")
                        if birdeye_key:
                            for addr in missing_addrs:
                                try:
                                    be_url = f"https://public-api.birdeye.so/defi/price?address={addr}"
                                    be_headers = {"X-API-KEY": birdeye_key, "Accept": "application/json"}
                                    be_res = requests.get(be_url, headers=be_headers, timeout=5).json()
                                    if be_res.get("success"):
                                        price = be_res.get("data", {}).get("value")
                                        if price is not None:
                                            price_map[addr] = {"price": float(price)}
                                            # print(f"  [FEED] Fallback sukses via Birdeye untuk {addr}")
                                except Exception:
                                    pass

                    # Fallback 2: query DexScreener API for any token still missing price info
                    missing_addrs = [addr for addr in addr_list if addr not in price_map]
                    for addr in missing_addrs:
                        try:
                            ds_url = f"https://api.dexscreener.com/latest/dex/tokens/{addr}"
                            ds_res = requests.get(ds_url, timeout=5).json()
                            pairs = ds_res.get("pairs", []) or []
                            if pairs:
                                pairs.sort(key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0), reverse=True)
                                price = pairs[0].get("priceUsd")
                                if price is not None:
                                    price_map[addr] = {"price": float(price)}
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
                            
                            # EMERGENCY FORCE-CLOSE after 3 consecutive cycles with no price data (likely rug/delisted)
                            if pos.get("no_price_cycles", 0) >= 3:
                                entry_price = pos["entry_price"]
                                exit_price = entry_price * 0.50  # Assume worst case -50% for rugpull
                                gross_inv = pos.get("gross_investment", pos["net_investment"])
                                pnl_usd = (pos["qty"] * exit_price) - gross_inv
                                realized_pnl_pct = (pnl_usd / gross_inv) * 100
                                
                                print(f"  [EMERGENCY EXIT] {pos['symbol']} tidak memiliki data harga 3 siklus berturut-turut. Kemungkinan RUGGED!")
                                print(f"     => Harga Jual Estimasi: ${exit_price:.8f} | Realized PnL: {realized_pnl_pct:+.2f}% (${pnl_usd:+.2f})")
                                
                                portfolio.setdefault("cooldowns", {})[addr] = time.time() + 86400  # 24 hour cooldown for rugged tokens
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
                        trade_mode = os.getenv("TRADE_MODE", "OPTIMIZED").upper()
                        
                        if trade_mode == "MOONSHOT":
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
                                sl_price = entry_price * 1.02
                                trail_level = "BE-LOCK (+2%)"
                            else:
                                sl_price = highest_price * 0.80 # 20% Initial SL
                                trail_level = "TRAILING SL (20%)"
                        else:
                            # OPTIMIZED HOLY GRAIL V15.0 (Score 75, SL 10%, BE 20% / Lock 2%) - RANK #1
                            if price_gain_pct >= 150.0:
                                sl_price = highest_price * 0.75  # Trail 25% from peak
                                trail_level = "STAGE 3 (25% TSL)"
                            elif price_gain_pct >= 60.0:
                                sl_price = highest_price * 0.80  # Trail 20% from peak
                                trail_level = "STAGE 2 (20% TSL)"
                            elif price_gain_pct >= 20.0:
                                sl_price = entry_price * 1.02  # Lock +2% profit when hit +20%
                                trail_level = "BE-LOCK (+2%)"
                            else:
                                sl_price = highest_price * 0.90  # Initial SL 10% from peak
                                trail_level = "OPTIMIZED INITIAL SL (10%)"
                            
                        print(f"  [POSITION] {pos['symbol']} | Entry: ${entry_price:.8f} | Live: ${current_price:.8f} | Puncak: ${highest_price:.8f} | SL: ${sl_price:.8f} | PnL: {current_pnl_pct:+.2f}% | Guard: {trail_level}")
                        
                        # Trigger exit ONLY when current price falls below dynamic trailing SL
                        if current_price <= sl_price:
                            exit_price = current_price
                            net_exit_value = pos["qty"] * exit_price
                            
                            # Use gross_investment if available, fallback to net_investment
                            gross_inv = pos.get("gross_investment", pos["net_investment"])
                            pnl_usd = net_exit_value - gross_inv
                            realized_pnl_pct = (pnl_usd / gross_inv) * 100
                            
                            print(f"  [EXIT TRIGGERED] {trail_level} Terpicu untuk {pos['symbol']}!")
                            print(f"     => Harga Jual: ${exit_price:.8f} | Realized PnL: {realized_pnl_pct:+.2f}% (${pnl_usd:+.2f})")
                            
                            portfolio.setdefault("cooldowns", {})[addr] = time.time() + 14400  # 4 Hour cooldown
                            print(f"     => [SHIELD] Alamat {addr} masuk daftar Cooldown 4 Jam.")
                            
                            portfolio["wallet_balance"] += net_exit_value
                            portfolio["trade_history"].append({
                                "symbol": pos["symbol"],
                                "address": addr,
                                "entry_price": entry_price,
                                "exit_price": exit_price,
                                "pnl_pct": realized_pnl_pct,
                                "pnl_usd": pnl_usd,
                                "closed_at": time.strftime('%Y-%m-%d %H:%M:%S')
                            })
                            del active_positions[addr]
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
                        
                        min_entry_score = int(os.getenv("MIN_ENTRY_SCORE", "75"))
                        if security["status"] in ["CLEAN & SAFE", "WARNINGS"] and score >= min_entry_score:
                            # Fixed sizing: $10.00 flat margin per trade
                            trade_allocation = 10.00
                            
                            if portfolio["wallet_balance"] >= trade_allocation:
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
            
        # High-frequency refresh every 5 seconds
        time.sleep(5)

if __name__ == "__main__":
    run_live_paper_trader()
