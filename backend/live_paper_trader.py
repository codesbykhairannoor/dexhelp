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
        print(f"[PAPER TRADER] Gagal menyimpan portofolio: {e}")

def run_live_paper_trader():
    portfolio = load_portfolio()
    
    print("=" * 80)
    print("🤖 SOLANA DEX PREDATOR - LIVE PAPER TRADING ENGINE (PRODUCTION V4)")
    print(f"💰 Virtual Wallet Balance: ${portfolio['wallet_balance']:.2f}")
    print("💼 Max Active Trades     : 2 Concurrent Positions Limit")
    print("🛡️ Compounding Margin     : 30% of Current Wallet Capital Per Trade")
    print("📈 Stop Loss Strategy    : 20% Trailing Stop Loss (No Ceiling!)")
    print("=" * 80)
    
    trailing_sl_pct = 0.20 # 20% Trailing SL
    
    # Costs per trade (Gas + Swap fee + Slippage)
    gas_fee = 0.12
    swap_fee_pct = 0.01
    slippage_pct = 0.02
    
    while True:
        try:
            print("\n" + "-" * 80)
            print(f"⏰ [SCAN CYCLE] {time.strftime('%Y-%m-%d %H:%M:%S')} | Mengaudit pasar live...")
            print("-" * 80)
            
            # --- PHASE 1: UPDATE LIVE ACTIVE POSITIONS ---
            active_positions = portfolio["active_positions"]
            closed_any = False
            
            if active_positions:
                print(f"💼 Memantau {len(active_positions)} posisi aktif secara live...")
                try:
                    # Production Fix 1: Bulk API Query to prevent rate limiting (429)
                    addr_list = list(active_positions.keys())
                    addr_str = ",".join(addr_list)
                    url = f"https://api.dexscreener.com/latest/dex/tokens/{addr_str}"
                    
                    r = requests.get(url, timeout=5)
                    # Production Fix 2: HTTP status validation and safe JSON parsing
                    if r.status_code == 200:
                        res = r.json()
                        pairs = res.get("pairs", []) or []
                        
                        # Map latest primary pool price per token
                        price_map = {}
                        for p in pairs:
                            t_addr = p.get("baseToken", {}).get("address")
                            liq = float(p.get("liquidity", {}).get("usd", 0) or 0)
                            price = float(p.get("priceUsd", 0) or 0)
                            if t_addr:
                                if t_addr not in price_map or liq > price_map[t_addr]["liq"]:
                                    price_map[t_addr] = {"price": price, "liq": liq}
                        
                        for addr, pos in list(active_positions.items()):
                            if addr in price_map and price_map[addr]["price"] > 0:
                                current_price = price_map[addr]["price"]
                                entry_price = pos["entry_price"]
                                highest_price = max(pos["highest_price"], current_price)
                                pos["highest_price"] = highest_price
                                
                                # Calculate trailing SL price
                                sl_price = highest_price * (1 - trailing_sl_pct)
                                current_pnl_pct = ((current_price - entry_price) / entry_price) * 100
                                
                                print(f"  🔹 {pos['symbol']} | Entry: ${entry_price:.8f} | Live: ${current_price:.8f} | Puncak: ${highest_price:.8f} | SL: ${sl_price:.8f} | PnL: {current_pnl_pct:+.2f}%")
                                
                                # Trigger Trailing Stop Loss
                                if current_price <= sl_price:
                                    net_exit_value = pos["qty"] * current_price
                                    pnl_usd = net_exit_value - pos["net_investment"]
                                    
                                    print(f"  🔴 [EXIT TRIGGERED] Trailing SL Terpicu untuk {pos['symbol']}!")
                                    print(f"     👉 Harga Jual: ${current_price:.8f} | Realized PnL: {current_pnl_pct:+.2f}% (${pnl_usd:+.2f})")
                                    
                                    portfolio["wallet_balance"] += net_exit_value
                                    portfolio["trade_history"].append({
                                        "symbol": pos["symbol"],
                                        "address": addr,
                                        "entry_price": entry_price,
                                        "exit_price": current_price,
                                        "pnl_pct": current_pnl_pct,
                                        "pnl_usd": pnl_usd,
                                        "closed_at": time.strftime('%Y-%m-%d %H:%M:%S')
                                    })
                                    del active_positions[addr]
                                    closed_any = True
                            else:
                                print(f"  ⚠️ Token {pos['symbol']} tidak ditemukan harganya pada API update ini.")
                    else:
                        print(f"  ⚠️ DexScreener API mengembalikan error HTTP: {r.status_code}")
                except Exception as e:
                    print(f"  ⚠️ Gagal melakukan bulk update harga: {e}")
            else:
                print("💼 Portofolio Posisi Aktif: KOSONG.")
                
            # --- PHASE 2: SCAN FOR NEW PREMIUM OPPORTUNITIES ---
            # Strict limit check: Max 2 active trades
            if len(active_positions) >= 2:
                print(f"⏳ [SCAN SKIPPED] Batas maksimum 2 posisi aktif terisi ({len(active_positions)}/2). Mengabaikan pembelian koin baru.")
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
                        
                        print(f"  🔍 Analisis {gem['symbol']} | Safety: {security['status']} | Predator Score: {score}/100")
                        
                        if security["status"] in ["CLEAN & SAFE", "WARNINGS"] and score >= 80:
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
                            
                            # Production Fix 4: Deduct 2% virtual slippage compensation for realistic metrics
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
                            
                            print(f"\n🎯 [AUTO BUY EXECUTED] Membeli {best_candidate['symbol']}!")
                            print(f"   👉 Harga Entry: ${best_candidate['price']:.8f} | Alokasi (30%): ${trade_allocation:.2f} (Net: ${net_investment:.2f})")
                            print(f"   👉 Predator Score: {best_candidate['predator_score']}/100 | Initial SL: ${best_candidate['price']*(1-trailing_sl_pct):.8f}")
                        else:
                            print(f"\n🚨 [BUY SKIPPED] Dana tidak cukup untuk membeli {best_candidate['symbol']}. Saldo: ${portfolio['wallet_balance']:.2f}")
            
            if closed_any:
                save_portfolio(portfolio)
                print(f"\n💰 Portofolio Diperbarui! Total Saldo Dompet Virtual: ${portfolio['wallet_balance']:.2f}")
                
        except Exception as e:
            print(f"[PAPER TRADER ERROR] Loop error: {e}")
            
        # Refresh every 60 seconds
        time.sleep(60)

if __name__ == "__main__":
    run_live_paper_trader()
