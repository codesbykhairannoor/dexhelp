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

def run_beast_simulation(
    sl_pct: float, 
    tp_pct: float, 
    be_active: bool, 
    fee_mode: str, 
    allocation_mode: str, 
    seed: int
) -> dict:
    random.seed(seed)
    
    # Starting conditions
    initial_capital = 1000.00
    wallet_balance = initial_capital
    active_positions = {}
    
    # Define Frictions
    if fee_mode == "REAL":
        gas_fee = 0.01
        swap_fee_pct = 0.0025
        slippage_pct = 0.005
    else:  # UNREALISTIC / OLD PAPER
        gas_fee = 0.12
        swap_fee_pct = 0.01
        slippage_pct = 0.02
        
    weights = [0.03, 0.95, 0.02]  # [DUMP, SCALP, MOONSHOT]
    
    total_trades = 0
    wins = 0
    losses = 0
    
    days = 30
    highest_balance = initial_capital
    max_drawdown = 0.0
    
    for day in range(1, days + 1):
        # Model 3 to 8 opportunities per day
        daily_opportunities = random.randint(3, 8)
        
        for _ in range(daily_opportunities):
            # 1. Update prices & exits of active positions
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
                        # Rugpull simulation (1% chance)
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
                            # Upward trend pump simulation
                            current_price *= random.uniform(0.98, 1.06)
                            if random.random() < 0.05:
                                current_price *= random.uniform(0.94, 0.98)
                                
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
                            # Standard SL Check
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
                                floor_sl = highest_price * (1 - sl_pct)
                                
                            if current_price <= floor_sl:
                                exit_price = floor_sl
                                trail_level = "SL"
                                break
                        else:
                            exit_price = current_price
                            
                    # Calculate realized PnL
                    net_exit_value = pos["qty"] * exit_price
                    pnl_usd = net_exit_value - pos["gross_investment"]
                    
                    wallet_balance += net_exit_value
                    total_trades += 1
                    
                    if pnl_usd >= 0:
                        wins += 1
                    else:
                        losses += 1
                        
                    del active_positions[symbol]
            
            # 2. Open new trades (up to 10 concurrent)
            if len(active_positions) < 10:
                if allocation_mode == "DYNAMIC":
                    trade_allocation = wallet_balance * 0.05  # 5% of balance per trade
                else:  # FLAT $10.00
                    trade_allocation = 10.00
                    
                if wallet_balance >= trade_allocation and trade_allocation > 0.5:
                    cost = gas_fee + (trade_allocation * swap_fee_pct) + (trade_allocation * slippage_pct)
                    net_investment = trade_allocation - cost
                    qty = net_investment / 1.0  # assume base entry price 1.0
                    
                    category = random.choices(["DUMP", "SCALP", "MOONSHOT"], weights=weights)[0]
                    lp_depth = random.choice([20000, 35000, 75000, 150000])
                    
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

def execute_beast_grid_search():
    # Grid variables
    sl_scenarios = [0.10, 0.12, 0.20]  # SL at 10%, 12%, 20%
    be_scenarios = [True, False]       # BE guard active or inactive
    fee_scenarios = ["REAL", "UNREAL"]  # Real Solana vs Unrealistic paper fees
    
    num_runs = 30  # Monte Carlo cycles for fast execution
    
    print("=" * 100)
    print("🛸 BEAST BACKTEST ENGINE: EXHAUSTIVE PARAMETER GRID-SEARCH ($1000 STARTING CAPITAL)")
    print("=" * 100)
    print(f"Running grid search over {len(sl_scenarios) * len(be_scenarios) * len(fee_scenarios)} combinations...")
    
    print("\n" + "=" * 100)
    print(f"{'FEES':<8} | {'BE-GUARD':<9} | {'STOP LOSS':<9} | {'AVG BALANCE':<13} | {'MEDIAN BAL':<13} | {'WIN RATE':<9} | {'MAX DD':<9} | {'AVG TRADES'}")
    print("-" * 100)
    
    for fee in fee_scenarios:
        for be in be_scenarios:
            for sl in sl_scenarios:
                run_ends = []
                run_wrs = []
                run_dds = []
                run_trades = []
                
                for i in range(num_runs):
                    seed = 999 + i * 19
                    res = run_beast_simulation(
                        sl_pct=sl,
                        tp_pct=10.0,
                        be_active=be,
                        fee_mode=fee,
                        allocation_mode="FLAT",
                        seed=seed
                    )
                    run_ends.append(res["ending_capital"])
                    run_wrs.append(res["win_rate"])
                    run_dds.append(res["max_drawdown"])
                    run_trades.append(res["total_trades"])
                    
                avg_bal = statistics.mean(run_ends)
                med_bal = statistics.median(run_ends)
                avg_wr = statistics.mean(run_wrs)
                avg_dd = statistics.mean(run_dds)
                avg_tr = statistics.mean(run_trades)
                
                fee_lbl = "REAL (0.85%)" if fee == "REAL" else "UNREAL (6.2%)"
                be_lbl = "ACTIVE" if be else "INACTIVE"
                sl_lbl = f"{int(sl*100)}%"
                
                print(f"{fee_lbl:<8} | {be_lbl:<9} | {sl_lbl:<9} | ${avg_bal:<12.2f} | ${med_bal:<12.2f} | {avg_wr:<7.1f}% | {avg_dd:<7.1f}% | {avg_tr:.1f}")
                
    print("=" * 100)

if __name__ == "__main__":
    execute_beast_grid_search()
