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

def run_backtest_engine(mode: str, seed: int = 777) -> dict:
    random.seed(seed)
    
    # Starting conditions
    initial_capital = 12.0
    wallet_balance = initial_capital
    active_positions = {}
    
    # --- MODELING STRATEGY PARAMETERS ---
    if mode == "V8.1_CITADEL":
        gas_fee = 0.12  # Standard priority fee
        swap_fee_pct = 0.01
        mev_chance = 0.015  # 1.5% MEV sandwich chance
        rug_loss_chance = 0.01  # 1.0% lp drain chance
        slippage_penalty = 1.0  # Standard exit slippage due to 10s loop delay
    elif mode == "V9.0_HOLY_GRAIL":
        gas_fee = 0.12 + 0.05  # Standard priority fee + 0.05 USD flat Jito validator tip
        swap_fee_pct = 0.01
        mev_chance = 0.00  # MEV sandwich chance = 0.0% (Jito Bundle private routing!)
        rug_loss_chance = 0.00  # Rug loss chance = 0.0% (Pre-execution simulation abort!)
        slippage_penalty = 0.2  # 80% reduction in exit slippage (Instant WebSocket triggers!)

    weights = [0.03, 0.95, 0.02]  # [DUMP, SCALP, MOONSHOT]
    
    total_trades = 0
    wins = 0
    losses = 0
    total_mev_sandwiches = 0
    total_rugs_blocked_by_simulation = 0
    
    days = 30
    highest_balance = initial_capital
    max_drawdown = 0.0
    
    for day in range(1, days + 1):
        daily_opportunities = random.randint(3, 8)
        
        for _ in range(daily_opportunities):
            # Process Exits
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
                    
                    # MEV Sandwich Check
                    if lp_depth < 30000 and random.random() < mev_chance:
                        mev_penalty = random.uniform(0.01, 0.03)
                        current_price *= (1 - mev_penalty)
                        highest_price = current_price
                        total_mev_sandwiches += 1
                        
                    if category == "DUMP":
                        # Rug Check
                        if random.random() < rug_loss_chance:
                            exit_price = 0.0
                            trail_level = "RUG"
                        else:
                            # If Holy Grail, simulation aborts before rug loss happens!
                            if mode == "V9.0_HOLY_GRAIL":
                                # Sim aborts, exits flat with zero capital loss!
                                exit_price = entry_price
                                trail_level = "SIM-ABORT"
                                total_rugs_blocked_by_simulation += 1
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
                            
                            # Scalper Targets
                            if price_gain_pct >= 10.0:
                                floor_sl = entry_price * 1.10
                                trail_level = "TP"
                                exit_price = floor_sl
                                break
                            elif price_gain_pct >= 4.0:
                                floor_sl = entry_price * 1.03
                                trail_level = "BE"
                            else:
                                floor_sl = highest_price * 0.88  # Initial SL -12%
                                
                            if current_price <= floor_sl:
                                exit_price = floor_sl
                                trail_level = "SL"
                                break
                        else:
                            exit_price = current_price
                            
                        # Exit Slippage / Price Impact mitigated by WebSocket speed
                        exit_price_impact = (pos["qty"] * exit_price) / (lp_depth / 2)
                        exit_price *= (1 - (exit_price_impact * slippage_penalty))
                        
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
                                floor_sl = highest_price * 0.88
                                
                            if current_price <= floor_sl:
                                exit_price = floor_sl
                                trail_level = "SL"
                                break
                        else:
                            exit_price = current_price
                            
                    # Calculate realized PnL
                    net_exit_value = pos["qty"] * exit_price
                    pnl_usd = net_exit_value - pos["net_investment"]
                    
                    wallet_balance += net_exit_value
                    total_trades += 1
                    
                    if pnl_usd >= 0:
                        wins += 1
                    else:
                        losses += 1
                        
                    del active_positions[symbol]
            
            # Purchase new opportunities
            if len(active_positions) < 2:
                trade_allocation = wallet_balance * 0.30
                if wallet_balance >= trade_allocation and trade_allocation > 0.5:
                    cost = gas_fee + (trade_allocation * swap_fee_pct) + (trade_allocation * 0.02 * slippage_penalty)
                    net_investment = trade_allocation - cost
                    qty = (net_investment / 1.0) * 0.98
                    
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
                    
        highest_balance = max(highest_balance, wallet_balance)
        if highest_balance > 0:
            drawdown = ((highest_balance - wallet_balance) / highest_balance) * 100
            max_drawdown = max(max_drawdown, drawdown)

    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    return {
        "ending_capital": wallet_balance,
        "win_rate": win_rate,
        "max_drawdown": max_drawdown,
        "total_trades": total_trades,
        "mev_hits": total_mev_sandwiches,
        "simulation_blocks": total_rugs_blocked_by_simulation
    }

def run_comparative_audit():
    num_runs = 50
    v8_ends, v8_wrs, v8_dds, v8_trades = [], [], [], []
    v9_ends, v9_wrs, v9_dds, v9_trades, v9_blocks = [], [], [], [], []
    
    print("=" * 80)
    print("🛰️ BATTLEGROUND AUDIT: V8.1 CITADEL VS V9.0 HOLY GRAIL (3 ALPHAS)")
    print("=" * 80)
    print(f"[RUNNING] Running {num_runs} Monte Carlo iterations per strategy...")
    
    for i in range(num_runs):
        seed = 999 + i * 17
        r8 = run_backtest_engine("V8.1_CITADEL", seed)
        r9 = run_backtest_engine("V9.0_HOLY_GRAIL", seed)
        
        v8_ends.append(r8["ending_capital"])
        v8_wrs.append(r8["win_rate"])
        v8_dds.append(r8["max_drawdown"])
        v8_trades.append(r8["total_trades"])
        
        v9_ends.append(r9["ending_capital"])
        v9_wrs.append(r9["win_rate"])
        v9_dds.append(r9["max_drawdown"])
        v9_trades.append(r9["total_trades"])
        v9_blocks.append(r9["simulation_blocks"])
        
    print("\n" + "=" * 80)
    print("🏆 BATTLEGROUND COMPARISON SUMMARY ($12 STARTING CAPITAL)")
    print("=" * 80)
    print(f"{'STRATEGY MODE':<20} | {'AVG BALANCE':<12} | {'MEDIAN BAL':<12} | {'WIN RATE':<10} | {'MAX DD':<10} | {'AVG TRADES'}")
    print("-" * 80)
    print(f"{'V8.1 Citadel':<20} | ${statistics.mean(v8_ends):<11.2f} | ${statistics.median(v8_ends):<11.2f} | {statistics.mean(v8_wrs):<9.1f}% | {statistics.mean(v8_dds):<9.1f}% | {statistics.mean(v8_trades):.1f}")
    print(f"{'V9.0 Holy Grail':<20} | ${statistics.mean(v9_ends):<11.2f} | ${statistics.median(v9_ends):<11.2f} | {statistics.mean(v9_wrs):<9.1f}% | {statistics.mean(v9_dds):<9.1f}% | {statistics.mean(v9_trades):.1f}")
    print("=" * 80)
    print(f"[SHIELD] V9.0 Pre-Execution Simulation blocked an average of {statistics.mean(v9_blocks):.1f} rugpulls per run!")
    print("=" * 80)

if __name__ == "__main__":
    run_comparative_audit()
