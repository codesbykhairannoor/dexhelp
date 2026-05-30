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

def run_realistic_simulation(
    sl_pct: float, 
    tp_pct: float, 
    be_active: bool, 
    seed: int
) -> dict:
    random.seed(seed)
    
    # Starting conditions
    initial_capital = 1000.00
    wallet_balance = initial_capital
    active_positions = {}
    
    # Realistic Solana Frictions
    gas_fee = 0.01
    swap_fee_pct = 0.0025
    slippage_pct = 0.005
    
    # REALISTIC SOLANA MEMECOIN DISTRIBUTION:
    # - 45% DUMP (Fails immediately or developer sells)
    # - 45% SCALP (Moderate volatility, pumps between 3% and 25%)
    # - 10% MOONSHOT (Strong pump, 30% to 200%)
    weights = [0.45, 0.45, 0.10]
    
    total_trades = 0
    wins = 0
    losses = 0
    
    days = 30
    highest_balance = initial_capital
    max_drawdown = 0.0
    
    for day in range(1, days + 1):
        daily_opportunities = random.randint(3, 8)
        
        for _ in range(daily_opportunities):
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
                    
                    if lp_depth < 30000 and random.random() < 0.02:
                        current_price *= 0.97
                        highest_price = current_price
                        
                    if category == "DUMP":
                        # Fast dump
                        for _ in range(steps):
                            current_price *= random.uniform(0.82, 0.98)
                        exit_price = current_price * 0.95
                        trail_level = "SL"
                            
                    elif category == "SCALP":
                        for step in range(steps):
                            # Volatile scalp: can pump up to 25% or drop
                            current_price *= random.uniform(0.95, 1.05)
                            highest_price = max(highest_price, current_price)
                            price_gain_pct = ((highest_price - entry_price) / entry_price) * 100
                            
                            # TP Check
                            if tp_pct > 0 and price_gain_pct >= tp_pct:
                                floor_sl = entry_price * (1 + (tp_pct / 100.0))
                                trail_level = "TP"
                                exit_price = floor_sl
                                break
                            # BE-Guard Check
                            elif be_active and price_gain_pct >= 4.0:
                                floor_sl = entry_price * 1.03
                                trail_level = "BE"
                            else:
                                floor_sl = highest_price * (1 - sl_pct)
                                
                            if current_price <= floor_sl:
                                exit_price = floor_sl
                                trail_level = "SL"
                                break
                        else:
                            exit_price = current_price
                        
                        # Exit price impact
                        exit_price_impact = (pos["qty"] * exit_price) / (lp_depth / 2)
                        exit_price *= (1 - exit_price_impact)
                        
                    else:  # MOONSHOT
                        for step in range(steps):
                            if step < 20:
                                current_price *= random.uniform(1.05, 1.25)
                            else:
                                current_price *= random.uniform(0.88, 1.02)
                            highest_price = max(highest_price, current_price)
                            price_gain_pct = ((highest_price - entry_price) / entry_price) * 100
                            
                            if price_gain_pct >= 150.0:
                                floor_sl = highest_price * 0.80
                                trail_level = "MEGA"
                            elif price_gain_pct >= 80.0:
                                floor_sl = entry_price * 1.50
                                trail_level = "STAGE2"
                            elif price_gain_pct >= 30.0:
                                floor_sl = entry_price * 1.15
                                trail_level = "STAGE1"
                            else:
                                floor_sl = highest_price * (1 - sl_pct)
                                
                            if current_price <= floor_sl:
                                exit_price = floor_sl
                                trail_level = "SL"
                                break
                        else:
                            exit_price = current_price
                            
                    net_exit_value = pos["qty"] * exit_price
                    pnl_usd = net_exit_value - pos["gross_investment"]
                    
                    wallet_balance += net_exit_value
                    total_trades += 1
                    
                    if pnl_usd >= 0:
                        wins += 1
                    else:
                        losses += 1
                        
                    del active_positions[symbol]
            
            # Open new trades
            if len(active_positions) < 10:
                trade_allocation = 10.00
                if wallet_balance >= trade_allocation:
                    cost = gas_fee + (trade_allocation * swap_fee_pct) + (trade_allocation * slippage_pct)
                    net_investment = trade_allocation - cost
                    qty = net_investment / 1.0
                    
                    category = random.choices(["DUMP", "SCALP", "MOONSHOT"], weights=weights)[0]
                    lp_depth = random.choice([15000, 25000, 50000, 100000])
                    
                    symbol = f"COIN_{random.randint(1000, 9999)}"
                    active_positions[symbol] = {
                        "category": category,
                        "lp_depth": lp_depth,
                        "gross_investment": trade_allocation,
                        "qty": qty
                    }
                    wallet_balance -= trade_allocation
                    
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

def run_realistic_grid_search():
    # Grid of scenarios
    sl_scenarios = [0.10, 0.12, 0.15, 0.20]  # Stop Losses
    tp_scenarios = [10.0, 15.0, 20.0, 30.0]  # Take Profits
    be_scenarios = [True, False]             # BE Guard
    
    num_runs = 40
    best_config = None
    best_balance = 0.0
    
    print("=" * 110)
    print("🎯 REALISTIC SOLANA MEMECOIN GRID SEARCH (45% DUMPS, 45% VOLATILE SCALPS, 10% MOONSHOTS)")
    print("=" * 110)
    print(f"{'BE-GUARD':<9} | {'STOP LOSS':<9} | {'TAKE PROFIT':<11} | {'AVG BALANCE':<13} | {'WIN RATE':<9} | {'MAX DD':<9} | {'AVG TRADES'}")
    print("-" * 110)
    
    results = []
    
    for be in be_scenarios:
        for sl in sl_scenarios:
            for tp in tp_scenarios:
                run_ends = []
                run_wrs = []
                run_dds = []
                run_trades = []
                
                for i in range(num_runs):
                    seed = 1000 + i * 23
                    res = run_realistic_simulation(sl, tp, be, seed)
                    run_ends.append(res["ending_capital"])
                    run_wrs.append(res["win_rate"])
                    run_dds.append(res["max_drawdown"])
                    run_trades.append(res["total_trades"])
                    
                avg_bal = statistics.mean(run_ends)
                avg_wr = statistics.mean(run_wrs)
                avg_dd = statistics.mean(run_dds)
                avg_tr = statistics.mean(run_trades)
                
                results.append({
                    "be": be,
                    "sl": sl,
                    "tp": tp,
                    "avg_bal": avg_bal,
                    "avg_wr": avg_wr,
                    "avg_dd": avg_dd,
                    "avg_tr": avg_tr
                })
                
                be_lbl = "ACTIVE" if be else "INACTIVE"
                sl_lbl = f"{int(sl*100)}%"
                tp_lbl = f"{int(tp)}%"
                
                print(f"{be_lbl:<9} | {sl_lbl:<9} | {tp_lbl:<11} | ${avg_bal:<12.2f} | {avg_wr:<7.1f}% | {avg_dd:<7.1f}% | {avg_tr:.1f}")
                
    # Find best config
    results.sort(key=lambda x: x["avg_bal"], reverse=True)
    best = results[0]
    
    print("=" * 110)
    print("🏆 OUTSTANDING WINNER CONFIGURATION FOR REAL MARKET CONDITIONS:")
    print("=" * 110)
    print(f"  -> BE-Guard       : {'ACTIVE' if best['be'] else 'INACTIVE'}")
    print(f"  -> Stop Loss (SL) : {int(best['sl']*100)}%")
    print(f"  -> Take Profit(TP): {int(best['tp'])}%")
    print(f"  -> Expected Profit: ${best['avg_bal'] - 1000.00:,.2f} USD")
    print(f"  -> Win Rate       : {best['avg_wr']:.1f}%")
    print(f"  -> Max Drawdown   : {best['avg_dd']:.1f}%")
    print("=" * 110)

if __name__ == "__main__":
    run_realistic_grid_search()
