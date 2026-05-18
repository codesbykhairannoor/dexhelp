import sys
import time
import random

# Fix Windows terminal encoding for Emojis
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def simulate_scenario(mode: str, seed: int = 12345):
    random.seed(seed)
    
    initial_capital = 12.0
    wallet_balance = initial_capital
    active_positions = {}
    
    # Gas, swap, and slippage fees
    gas_fee = 0.12
    swap_fee_pct = 0.01
    slippage_pct = 0.02
    
    total_trades_count = 0
    total_wins = 0
    total_losses = 0
    total_scams_blocked = 0
    
    # Configure variables based on Mode
    if mode == "AGRESIF":
        # Loose filter (Score 60+), high dump risk, massive trade count
        dump_rate = 0.08
        scalp_rate = 0.42
        moonshot_rate = 0.50
        min_opps, max_opps = 6, 10
    else:
        # Strict filter (Score 80+), ultra low dump risk, low trade count
        dump_rate = 0.005
        scalp_rate = 0.445
        moonshot_rate = 0.55
        min_opps, max_opps = 1, 2
        
    weights = [dump_rate, scalp_rate, moonshot_rate]
    days = 30
    
    for day in range(1, days + 1):
        daily_opportunities = random.randint(min_opps, max_opps)
        
        # Scams blocked is proportional to scanning frequency
        day_scams_blocked = random.randint(30, 50) if mode == "AGRESIF" else random.randint(12, 18)
        total_scams_blocked += day_scams_blocked
        
        for opp in range(daily_opportunities):
            # 1. Update/Close active positions first
            if active_positions:
                for symbol, pos in list(active_positions.items()):
                    category = pos["category"]
                    entry_price = 1.0
                    highest_price = entry_price
                    current_price = entry_price
                    
                    # BE Guard & Dynamic SL calibration
                    trailing_sl_pct = 0.10 if category == "SCALP" else 0.25
                    breakeven_triggered = False
                    steps = 30
                    exit_price = entry_price
                    
                    if category == "DUMP":
                        for _ in range(steps):
                            current_price *= random.uniform(0.70, 0.96)
                            highest_price = max(highest_price, current_price)
                            # Slippage slippage during panic sell
                            if current_price <= highest_price * 0.85:
                                exit_price = highest_price * 0.80
                                break
                        else:
                            exit_price = current_price
                    elif category == "SCALP":
                        for step in range(steps):
                            if step < 10: 
                                current_price *= random.uniform(0.98, 1.06)
                            else: 
                                current_price *= random.uniform(0.95, 1.01)
                            highest_price = max(highest_price, current_price)
                            
                            price_gain_pct = ((current_price - entry_price) / entry_price) * 100
                            if price_gain_pct >= 15.0:
                                breakeven_triggered = True
                                
                            floor_sl = (entry_price * 0.98) if breakeven_triggered else (highest_price * (1 - trailing_sl_pct))
                            if current_price <= floor_sl:
                                exit_price = floor_sl
                                break
                        else:
                            exit_price = current_price
                    else:  # MOONSHOT
                        for step in range(steps):
                            if step < 20: 
                                current_price *= random.uniform(1.00, 1.15)
                            else: 
                                current_price *= random.uniform(0.88, 1.00)
                            highest_price = max(highest_price, current_price)
                            
                            price_gain_pct = ((current_price - entry_price) / entry_price) * 100
                            if price_gain_pct >= 15.0:
                                breakeven_triggered = True
                                
                            floor_sl = (entry_price * 0.98) if breakeven_triggered else (highest_price * (1 - trailing_sl_pct))
                            if current_price <= floor_sl:
                                exit_price = floor_sl
                                break
                        else:
                            exit_price = current_price
                    
                    net_exit_value = pos["qty"] * exit_price
                    pnl_usd = net_exit_value - pos["net_investment"]
                    
                    wallet_balance += net_exit_value
                    
                    if pnl_usd > 0:
                        total_wins += 1
                    else:
                        total_losses += 1
                        
                    total_trades_count += 1
                    del active_positions[symbol]
            
            # 2. Open new positions if limits allow (Max 2 active)
            if len(active_positions) < 2:
                if wallet_balance >= 500.0:
                    trade_allocation = 100.0
                else:
                    trade_allocation = wallet_balance * 0.30
                    
                if trade_allocation >= 0.5 and wallet_balance >= trade_allocation:
                    cost_per_trade = gas_fee + (trade_allocation * swap_fee_pct) + (trade_allocation * slippage_pct)
                    net_investment = trade_allocation - cost_per_trade
                    qty = (net_investment / 1.0) * 0.98
                    
                    category = random.choices(["DUMP", "SCALP", "MOONSHOT"], weights=weights)[0]
                    symbol = f"GEM{total_trades_count + len(active_positions) + 1:03d}"
                    
                    active_positions[symbol] = {
                        "symbol": symbol,
                        "net_investment": net_investment,
                        "qty": qty,
                        "category": category
                    }
                    wallet_balance -= trade_allocation
                    
    return {
        "balance": wallet_balance,
        "trades": total_trades_count,
        "wins": total_wins,
        "losses": total_losses,
        "scams": total_scams_blocked
    }

def run_comparison():
    print("=" * 80)
    print("⚔️ SIDE-BY-SIDE BENCHMARK: AGRESSIVE VS CONSERVATIVE FREQUENCY")
    print("=" * 80)
    print("[SYSTEM] Starting comparison over 30 Days | Seed: 12345")
    time.sleep(1)
    
    agresif = simulate_scenario("AGRESIF")
    selektif = simulate_scenario("SELEKTIF")
    
    print("\n📊 HASIL KOMPARASI AKHIR (SIDE-BY-SIDE):")
    print("-" * 80)
    print(f"| Parameter Kinerja      | AGRESIF MODE (Banyak Trade)  | SELEKTIF MODE (Sedikit Trade)|")
    print("-" * 80)
    print(f"| Modal Awal             | $12.00                      | $12.00                       |")
    print(f"| Saldo Akhir Net        | ${agresif['balance']:<26,.2f} | ${selektif['balance']:<28,.2f} |")
    print(f"| Akumulasi Yield        | +{((agresif['balance']-12)/12)*100:<25,.2f}% | +{((selektif['balance']-12)/12)*100:<27,.2f}% |")
    print(f"| Total Trade Dieksekusi | {agresif['trades']:<28} | {selektif['trades']:<29} |")
    print(f"| Win Rate Nominal       | {(agresif['wins']/agresif['trades'])*100:<26.1f}% | {(selektif['wins']/selektif['trades'])*100:<28.1f}% |")
    print(f"| Kemenangan (Wins)      | {agresif['wins']:<28} | {selektif['wins']:<29} |")
    print(f"| Kekalahan (Losses)     | {agresif['losses']:<28} | {selektif['losses']:<29} |")
    print(f"| Koin Scam Diblokir     | {agresif['scams']:<28} | {selektif['scams']:<29} |")
    print("-" * 80)
    print("\n💡 PEMBELAJARAN STRATEGIS (EXECUTIVE INSIGHTS):")
    
    # Compute Transaction Frictions for both
    # 0.12 gas + 3% slip/swap on $100 cap trade is approx $3.12 friction per trade
    agresif_friction = agresif['trades'] * 3.12
    selektif_friction = selektif['trades'] * 3.12
    
    print(f"  1. Estimasi Biaya Transaksi (Friction Cost):")
    print(f"     - AGRESIF   : ${agresif_friction:,.2f} (Memakan PnL akibat gas & slippage)")
    print(f"     - SELEKTIF  : ${selektif_friction:,.2f} (Sangat hemat & efisien)")
    print(f"  2. Hasil Akhir:")
    if agresif['balance'] > selektif['balance']:
        print("     => AGRESIF MODE menghasilkan saldo lebih tinggi karena volume transaksi murni")
        print("        berhasil memancing lebih banyak Moonshots walau terkena banyak dump.")
    else:
        print("     => SELEKTIF MODE menghasilkan saldo lebih tinggi karena menghindari 'Friction Trap'")
        print("        (biaya gas dan koin sampah) sehingga pertumbuhan modal terkunci aman.")
    print("=" * 80)

if __name__ == "__main__":
    run_comparison()
