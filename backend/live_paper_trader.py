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
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "wallet_balance": 100.00,  # Virtual Starting Wallet
        "active_positions": {},    # token_address -> trade_info
        "trade_history": []        # List of completed simulated trades
    }

def save_portfolio(portfolio: dict):
    try:
        with open(PORTFOLIO_FILE, "w") as f:
            json.dump(portfolio, f, indent=4)
    except Exception as e:
        print(f"[ERROR] Gagal menyimpan portofolio: {e}")

def run_live_paper_trader():
    portfolio = load_portfolio()
    
    print("=" * 80)
    print("[SYSTEM] SOLANA DEX PREDATOR - LIVE PAPER TRADING ENGINE (PRODUCTION V5)")
    print(f"[INFO] Virtual Wallet Balance: ${portfolio['wallet_balance']:.2f}")
    print("[INFO] Max Active Trades     : 2 Concurrent Positions Limit")
    print("[INFO] Compounding Margin     : 30% of Current Wallet Capital Per Trade")
    print("[INFO] Stop Loss Strategy    : 20% Trailing Stop Loss (No Ceiling!)")
    print("=" * 80)
    
    trailing_sl_pct = 0.20 # 20% Trailing SL
    
    # Costs per trade (Gas + Swap fee + Slippage)
    gas_fee = 0.12
    swap_fee_pct = 0.01
    slippage_pct = 0.02
    
    while True:
        try:
            print("\n" + "-" * 80)
            print(f"[SCAN CYCLE] {time.strftime('%Y-%m-%d %H:%M:%S')} | Mengaudit pasar live...")
            print("-" * 80)
            
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
                    # HTTP status validation and safe JSON parsing
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
                                
                                # Dynamic Step-Trailing (Trailing Tangga) & Positive BE-Guard Logic
                                price_gain_pct = ((highest_price - entry_price) / entry_price) * 100
                                current_pnl_pct = ((current_price - entry_price) / entry_price) * 100
                                
                                if price_gain_pct >= 200.0:
                                    sl_price = highest_price * 0.75  # Mega Moonshot Trailing -25%
                                    trail_level = "MEGA-TRAIL (-25% Peak)"
                                elif price_gain_pct >= 100.0:
                                    sl_price = entry_price * 1.65  # Lock +65% profit
                                    trail_level = "STAGE 2 (+65%)"
                                elif price_gain_pct >= 40.0:
                                    sl_price = entry_price * 1.20  # Lock +20% profit
                                    trail_level = "STAGE 1 (+20%)"
                                elif price_gain_pct >= 15.0:
                                    sl_price = entry_price * 1.03  # Positive Breakeven (+3% covers fee)
                                    trail_level = "BE-GUARD (+3%)"
                                else:
                                    sl_price = highest_price * 0.90  # Normal tight trailing 10%
                                    trail_level = "NORMAL TIGHT (10%)"
                                    
                                print(f"  [POSITION] {pos['symbol']} | Entry: ${entry_price:.8f} | Live: ${current_price:.8f} | Puncak: ${highest_price:.8f} | SL: ${sl_price:.8f} | PnL: {current_pnl_pct:+.2f}% | Guard: {trail_level}")
                                
                                # Trigger Trailing Stop Loss
                                if current_price <= sl_price:
                                    exit_price = sl_price
                                    net_exit_value = pos["qty"] * exit_price
                                    pnl_usd = net_exit_value - pos["net_investment"]
                                    realized_pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                                    
                                    print(f"  [EXIT TRIGGERED] {trail_level} Terpicu untuk {pos['symbol']}!")
                                    print(f"     => Harga Jual: ${exit_price:.8f} | Realized PnL: {realized_pnl_pct:+.2f}% (${pnl_usd:+.2f})")
                                    
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
                        print(f"  [WARN] DexScreener API mengembalikan error HTTP: {r.status_code}")
                except Exception as e:
                    print(f"  [WARN] Gagal melakukan bulk update harga: {e}")
            else:
                print("[INFO] Portofolio Posisi Aktif: KOSONG.")
                
            # --- PHASE 2: SCAN FOR NEW PREMIUM OPPORTUNITIES ---
            # Strict limit check: Max 2 active trades
            if len(active_positions) >= 2:
                print(f"[SCAN] Limit 2 posisi aktif terisi ({len(active_positions)}/2). Mengabaikan scan koin baru.")
            else:
                candidates = _fetch_candidates()
                if candidates:
                    candidates.sort(key=lambda x: x.get("volume_5m", 0), reverse=True)
                    top_candidates = candidates[:5]
                    
                    best_candidate = None
                    best_score = 0
                    
                    for gem in top_candidates:
                        addr = gem["address"]
                        if addr in active_positions:
                            continue
                            
                        security = check_token_security(gem["chain"], addr)
                        score = calculate_gem_score(gem, security)
                        
                        print(f"  [SCAN] Analisis {gem['symbol']} | Safety: {security['status']} | Score: {score}/100")
                        
                        if security["status"] in ["CLEAN & SAFE", "WARNINGS"] and score >= 70:
                            if score > best_score:
                                best_score = score
                                best_candidate = gem
                                best_candidate["security_status"] = security["status"]
                                best_candidate["predator_score"] = score
                                
                    # --- PHASE 3: EXECUTE AUTO VIRTUAL BUY ---
                    if best_candidate:
                        addr = best_candidate["address"]
                        # Compounding Money Management: 30% of current wallet balance
                        trade_allocation = portfolio["wallet_balance"] * 0.30
                        
                        if portfolio["wallet_balance"] >= trade_allocation and trade_allocation > 1.0:
                            cost_per_trade = gas_fee + (trade_allocation * swap_fee_pct) + (trade_allocation * slippage_pct)
                            net_investment = trade_allocation - cost_per_trade
                            
                            # Deduct 2% virtual slippage compensation for realistic metrics
                            qty = (net_investment / best_candidate["price"]) * 0.98
                            
                            # Add new position
                            active_positions[addr] = {
                                "symbol": best_candidate["symbol"],
                                "name": best_candidate["name"],
                                "entry_price": best_candidate["price"],
                                "highest_price": best_candidate["price"],
                                "net_investment": net_investment,
                                "qty": qty,
                                "entry_time": time.strftime('%Y-%m-%d %H:%M:%S')
                            }
                            
                            portfolio["wallet_balance"] -= trade_allocation
                            closed_any = True
                            
                            print(f"\n[BUY EXECUTED] Membeli {best_candidate['symbol']}!")
                            print(f"   => Harga Entry: ${best_candidate['price']:.8f} | Alokasi (30%): ${trade_allocation:.2f} (Net: ${net_investment:.2f})")
                            print(f"   => Score: {best_candidate['predator_score']}/100 | Initial SL: ${best_candidate['price']*(1-trailing_sl_pct):.8f}")
                        else:
                            print(f"\n[SCAN] Dana tidak cukup untuk membeli {best_candidate['symbol']}. Saldo: ${portfolio['wallet_balance']:.2f}")
            
            if closed_any:
                save_portfolio(portfolio)
                print(f"\n[PORTFOLIO] Portofolio Diperbarui! Total Saldo Dompet Virtual: ${portfolio['wallet_balance']:.2f}")
                
        except Exception as e:
            print(f"[ERROR] Loop error: {e}")
            
        # Refresh every 60 seconds
        time.sleep(60)

if __name__ == "__main__":
    run_live_paper_trader()
