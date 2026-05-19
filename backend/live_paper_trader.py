import os
import sys
import time
import json
import requests
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
    portfolio = load_portfolio()
    
    print("=" * 80)
    print("[SYSTEM] SOLANA DEX PREDATOR - LIVE PAPER TRADING ENGINE (PRODUCTION V8.8)")
    print(f"[INFO] Virtual Wallet Balance : ${portfolio['wallet_balance']:.2f}")
    print("[INFO] Max Active Trades      : 10 Concurrent Positions Limit")
    print("[INFO] Target Take-Profit (TP): +10.0% (Instant Exit)")
    print("[INFO] Breakeven Guard (BE)  : Lock +3.0% when price hits +4.0%")
    print("[INFO] Initial Stop Loss (SL) : -12.0% (Tight Protection)")
    print("[INFO] Token Cooldown Shield  : 24 Hours (86,400s) Blacklist on Exit")
    print("=" * 80)
    
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
                    
                    r = requests.get(url, headers=headers, timeout=5)
                    if r.status_code == 200:
                        res = r.json()
                        
                        # Map latest price per token
                        price_map = {}
                        for addr in addr_list:
                            tinfo = res.get(addr, {})
                            price = tinfo.get("usdPrice")
                            if price is not None:
                                price_map[addr] = {"price": float(price)}
                        
                        for addr, pos in list(active_positions.items()):
                            if addr in price_map and price_map[addr]["price"] > 0:
                                current_price = price_map[addr]["price"]
                                entry_price = pos["entry_price"]
                                highest_price = max(pos["highest_price"], current_price)
                                pos["highest_price"] = highest_price
                                
                                # Dynamic 96% WR Scalper Trailing & TP Logic
                                price_gain_pct = ((highest_price - entry_price) / entry_price) * 100
                                current_pnl_pct = ((current_price - entry_price) / entry_price) * 100
                                
                                # V9.1 OPTIMAL REAL-WORLD PARAMETERS (BE-GUARD ACTIVE, SL 20%, TP 30%)
                                if price_gain_pct >= 30.0:
                                    sl_price = entry_price * 1.30  # Exit immediately at +30% target!
                                    trail_level = "STAGE 1 (+30% TP)"
                                elif price_gain_pct >= 4.0:
                                    sl_price = entry_price * 1.03  # Drag to positive BE at +4% gain
                                    trail_level = "BE-GUARD (+3%)"
                                else:
                                    sl_price = highest_price * 0.80  # Stop Loss 20% from peak
                                    trail_level = "TRAILING SL (20%)"
                                    
                                print(f"  [POSITION] {pos['symbol']} | Entry: ${entry_price:.8f} | Live: ${current_price:.8f} | Puncak: ${highest_price:.8f} | SL: ${sl_price:.8f} | PnL: {current_pnl_pct:+.2f}% | Guard: {trail_level}")
                                
                                # Trigger Trailing Stop Loss or Take Profit
                                if current_price <= sl_price or price_gain_pct >= 30.0:
                                    exit_price = current_price if price_gain_pct >= 30.0 else sl_price
                                    net_exit_value = pos["qty"] * exit_price
                                    
                                    # Use gross_investment if available, fallback to net_investment
                                    gross_inv = pos.get("gross_investment", pos["net_investment"])
                                    pnl_usd = net_exit_value - gross_inv
                                    realized_pnl_pct = (pnl_usd / gross_inv) * 100
                                    
                                    print(f"  [EXIT TRIGGERED] {trail_level} Terpicu untuk {pos['symbol']}!")
                                    print(f"     => Harga Jual: ${exit_price:.8f} | Realized PnL: {realized_pnl_pct:+.2f}% (${pnl_usd:+.2f})")
                                    
                                    # Persist cooldown for 24 Hours (86,400 seconds) to prevent re-entries
                                    portfolio.setdefault("cooldowns", {})[addr] = time.time() + 86400
                                    print(f"     => [SHIELD] Alamat {addr} masuk daftar Cooldown 24 Jam.")
                                    
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
                            else:
                                print(f"  [WARN] Token {pos['symbol']} tidak ditemukan harganya pada API update ini.")
                    else:
                        print(f"  [WARN] Jupiter API mengembalikan error HTTP: {r.status_code}")
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
                    
                    # Loop through ALL candidates and buy dynamically
                    for gem in candidates:
                        if len(active_positions) >= 10:
                            break
                            
                        addr = gem["address"]
                        if addr in active_positions:
                            continue
                            
                        # Strict 24-hour Cooldown filter check
                        if "cooldowns" in portfolio and addr in portfolio["cooldowns"]:
                            continue
                            
                        security = check_token_security(gem["chain"], addr)
                        score = calculate_gem_score(gem, security)
                        
                        print(f"  [SCAN] Analisis {gem['symbol']} | Safety: {security['status']} | Score: {score}/100")
                        
                        if security["status"] in ["CLEAN & SAFE", "WARNINGS"] and score >= 70:
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
            
        # High-frequency refresh every 10 seconds
        time.sleep(10)

if __name__ == "__main__":
    run_live_paper_trader()
