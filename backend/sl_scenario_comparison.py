import os
import sys
import random
import statistics

# Fix Windows terminal encoding for Emojis
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def run_simulation_run(initial_sl_pct: float, seed: int) -> dict:
    random.seed(seed)
    
    # Starting conditions
    initial_capital = 12.0
    wallet_balance = initial_capital
    active_positions = {}
    
    # Frictions
    gas_fee = 0.12
    swap_fee_pct = 0.01
    
    # 95% scalp, 3% dumps/rugs, 2% moonshots
    weights = [0.03, 0.95, 0.02]
    
    total_trades = 0
    wins = 0
    losses = 0
    
    days = 30
    highest_balance = initial_capital
    max_drawdown = 0.0
    
    for day in range(1, days + 1):
        daily_opportunities = random.randint(3, 8)
        
        for _ in range(daily_opportunities):
            # Process exits
            if active_positions:
                for symbol, pos in list(active_positions.items()):
                    category = pos["category"]
                    lp_depth = pos["lp_depth"]
                    entry_price = 1.0
                    highest_price = entry_price
                    current_price = entry_price
                    
                    steps = 40
                    exit_price = entry_price
                    trail_level = "ENTRY"
                    
                    # 1.5% MEV sandwich chance
                    if lp_depth < 30000 and random.random() < 0.015:
                        current_price *= 0.98
                        highest_price = current_price
                        
                    if category == "DUMP":
                        # Rugpull check (1% chance)
                        if random.random() < 0.01:
                            exit_price = 0.0
                            trail_level = "RUG"
                        else:
                            for _ in range(steps):
                                current_price *= random.uniform(0.70, 0.96)
                            exit_price = current_price * 0.95
                            trail_level = "SL"
                            
                    elif category == "SCALP":
                        for step in range(steps):
                            current_price *= random.uniform(0.98, 1.06)
                            if random.random() < 0.05:
                                current_price *= random.uniform(0.94, 0.98)
                                
                            highest_price = max(highest_price, current_price)
                            price_gain_pct = ((highest_price - entry_price) / entry_price) * 100
                            
                            # Logika Scalper
                            if price_gain_pct >= 10.0:
                                floor_sl = entry_price * 1.10  # TP +10% target
                                trail_level = "TP"
                                exit_price = floor_sl
                                break
                            elif price_gain_pct >= 4.0:
                                floor_sl = entry_price * 1.03  # BE-Guard +3%
                                trail_level = "BE"
                            else:
                                floor_sl = highest_price * (1 - initial_sl_pct)  # Dynamic Variable SL
                                
                            if current_price <= floor_sl:
                                exit_price = floor_sl
                                trail_level = "SL"
                                break
                        else:
                            exit_price = current_price
                            
                        # Exit slippage
                        exit_price_impact = (pos["qty"] * exit_price) / (lp_depth / 2)
                        exit_price *= (1 - exit_price_impact)
                        
                    else:  # MOONSHOT
                        for step in range(steps):
                            if step < 25:
                                current_price *= random.uniform(1.02, 1.20)
                            else:
                                current_price *= random.uniform(0.85, 1.01)
                            highest_price = max(highest_price, current_price)
                            price_gain_pct = ((highest_price - entry_price) / entry_price) * 100
                            
                            if price_gain_pct >= 200.0:
                                floor_sl = highest_price * 0.75
                                trail_level = "MEGA"
                            elif price_gain_pct >= 100.0:
                                floor_sl = entry_price * 1.65
                                trail_level = "STAGE2"
                            elif price_gain_pct >= 40.0:
                                floor_sl = entry_price * 1.20
                                trail_level = "STAGE1"
                            elif price_gain_pct >= 15.0:
                                floor_sl = entry_price * 1.03
                                trail_level = "BE"
                            else:
                                floor_sl = highest_price * (1 - initial_sl_pct)
                                
                            if current_price <= floor_sl:
                                exit_price = floor_sl
                                trail_level = "SL"
                                break
                        else:
                            exit_price = current_price
                            
                    # Process realized transaction
                    net_exit_value = pos["qty"] * exit_price
                    pnl_usd = net_exit_value - pos["net_investment"]
                    
                    wallet_balance += net_exit_value
                    total_trades += 1
                    
                    if pnl_usd >= 0:
                        wins += 1
                    else:
                        losses += 1
                        
                    del active_positions[symbol]
            
            # Purchase new opportunities (max 2 active)
            if len(active_positions) < 2:
                # MM: 30% of wallet capital
                trade_allocation = wallet_balance * 0.30
                if wallet_balance >= trade_allocation and trade_allocation > 0.5:
                    cost = gas_fee + (trade_allocation * 0.01) + (trade_allocation * 0.02)
                    net_investment = trade_allocation - cost
                    qty = (net_investment / 1.0) * 0.98  # assume starting price 1.0
                    
                    category = random.choices(["DUMP", "SCALP", "MOONSHOT"], weights=weights)[0]
                    lp_depth = random.choice([20000, 35000, 75000, 150000])
                    
                    symbol = f"COIN_{random.randint(1000, 9999)}"
                    active_positions[symbol] = {
                        "category": category,
                        "lp_depth": lp_depth,
                        "net_investment": net_investment,
                        "qty": qty
                    }
                    wallet_balance -= trade_allocation
                    
        # Track drawdown per day
        highest_balance = max(highest_balance, wallet_balance)
        if highest_balance > 0:
            drawdown = ((highest_balance - wallet_balance) / highest_balance) * 100
            max_drawdown = max(max_drawdown, drawdown)

    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    return {
        "ending_capital": wallet_balance,
        "win_rate": win_rate,
        "max_drawdown": max_drawdown,
        "total_trades": total_trades
    }

def run_monte_carlo():
    scenarios = {
        "Scenario A (10% SL)": 0.10,
        "Scenario B (12% SL)": 0.12,
        "Scenario C (15% SL)": 0.15,
        "Scenario D (20% SL)": 0.20
    }
    
    num_runs = 50
    results_summary = {}
    
    print("=" * 80)
    print("🛸 QUANT SCENARIO AUDITOR: MONTE CARLO MONSTER SIMULATION (50 RUNS PER SCENARIO)")
    print("=" * 80)
    
    for name, sl_val in scenarios.items():
        print(f"[RUNNING] Evaluasi {name}...")
        
        run_ends = []
        run_wrs = []
        run_dds = []
        run_trades = []
        
        for i in range(num_runs):
            # Dynamic seed for each independent run
            seed = 777 + i * 13
            res = run_simulation_run(sl_val, seed)
            
            run_ends.append(res["ending_capital"])
            run_wrs.append(res["win_rate"])
            run_dds.append(res["max_drawdown"])
            run_trades.append(res["total_trades"])
            
        results_summary[name] = {
            "avg_capital": statistics.mean(run_ends),
            "median_capital": statistics.median(run_ends),
            "avg_win_rate": statistics.mean(run_wrs),
            "avg_drawdown": statistics.mean(run_dds),
            "avg_trades": statistics.mean(run_trades)
        }
        
    print("\n" + "=" * 80)
    print("🏆 HASIL AKHIR AUDIT KOMPARASI MONTE CARLO SCENARIO STOP LOSS")
    print("=" * 80)
    print(f"{'SCENARIO NAME':<20} | {'AVG BALANCE':<12} | {'MEDIAN BAL':<12} | {'WIN RATE':<10} | {'MAX DD':<10} | {'AVG TRADES'}")
    print("-" * 80)
    
    for name, stats in results_summary.items():
        print(f"{name:<20} | ${stats['avg_capital']:<11.2f} | ${stats['median_capital']:<11.2f} | {stats['avg_win_rate']:<9.1f}% | {stats['avg_drawdown']:<9.1f}% | {stats['avg_trades']:.1f}")
    print("=" * 80)

if __name__ == "__main__":
    run_monte_carlo()
