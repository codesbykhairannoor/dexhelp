import sys
import time
import random

def run_sim(trailing_sl_pct, take_profit_pct, dump_w, scalp_w, moon_w):
    random.seed(42)
    initial_capital = 100.0
    trade_allocation_pct = 0.10
    
    current_wallet = initial_capital
    gas_fee = 0.05
    swap_fee_pct = 0.005
    slippage_pct = 0.01
    
    wins = 0
    losses = 0
    
    wallet_history = [initial_capital]
    
    for trade_counter in range(1, 1001):
        if current_wallet < 5.0:
            break
            
        trade_allocation = current_wallet * trade_allocation_pct
        cost_per_trade = gas_fee + (trade_allocation * swap_fee_pct) + (trade_allocation * slippage_pct)
        net_entry = trade_allocation - cost_per_trade
        
        category = random.choices(["DUMP", "SCALP", "MOONSHOT"], weights=[dump_w, scalp_w, moon_w])[0]
        
        entry_price = 1.0
        highest_price = entry_price
        current_price = entry_price
        steps = 40
        exit_price = entry_price
        
        if category == "DUMP":
            for _ in range(steps):
                current_price *= random.uniform(0.85, 1.01)
                highest_price = max(highest_price, current_price)
                sl_price = highest_price * (1 - trailing_sl_pct)
                if current_price >= entry_price * (1 + take_profit_pct):
                    exit_price = current_price
                    break
                if current_price <= sl_price:
                    exit_price = sl_price
                    break
            else:
                exit_price = current_price
                
        elif category == "SCALP":
            for step in range(steps):
                if step < 15:
                    current_price *= random.uniform(0.97, 1.05)
                else:
                    current_price *= random.uniform(0.92, 1.02)
                    
                highest_price = max(highest_price, current_price)
                sl_price = highest_price * (1 - trailing_sl_pct)
                
                if current_price >= entry_price * (1 + take_profit_pct):
                    exit_price = current_price
                    break
                if current_price <= sl_price:
                    exit_price = sl_price
                    break
            else:
                exit_price = current_price
                
        else:
            # MOONSHOT
            for step in range(steps):
                if step < 25:
                    current_price *= random.uniform(0.99, 1.15)
                else:
                    current_price *= random.uniform(0.88, 1.02)
                    
                highest_price = max(highest_price, current_price)
                
                if highest_price >= 2.0:
                    sl_price = highest_price * 0.70
                else:
                    sl_price = highest_price * (1 - trailing_sl_pct)
                    
                if current_price >= entry_price * (1 + take_profit_pct * 2): # Let moonshot run longer
                    exit_price = current_price
                    break
                    
                if current_price <= sl_price:
                    exit_price = sl_price
                    break
            else:
                exit_price = current_price
        
        trade_yield_pct = ((exit_price - entry_price) / entry_price) * 100
        trade_pnl = net_entry * (trade_yield_pct / 100)
        
        if trade_pnl > 0:
            wins += 1
        else:
            losses += 1
            
        current_wallet += trade_pnl
        wallet_history.append(current_wallet)

    win_rate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0
    max_peak = initial_capital
    max_dd = 0.0
    for w in wallet_history:
        if w > max_peak: max_peak = w
        dd = ((max_peak - w) / max_peak) * 100
        if dd > max_dd: max_dd = dd
        
    return win_rate, current_wallet, max_dd

scenarios = [
    {"name": "No Fixed TP (Let winners run)", "tsl": 0.20, "tp": 999.0},
    {"name": "Aggressive Scalper (TP 15%, SL 10%)", "tsl": 0.10, "tp": 0.15},
    {"name": "Balanced (TP 30%, SL 15%)", "tsl": 0.15, "tp": 0.30},
    {"name": "Holy Grail Mode (TP 20%, SL 8%)", "tsl": 0.08, "tp": 0.20},
    {"name": "Safe Haven (TP 10%, SL 5%)", "tsl": 0.05, "tp": 0.10}
]

print("=== SCENARIO TESTING ===")
for s in scenarios:
    wr, bal, dd = run_sim(s["tsl"], s["tp"], 0.10, 0.60, 0.30)
    print(f"Scenario: {s['name']}")
    print(f"  Win Rate: {wr:.1f}% | Max DD: {dd:.1f}% | Final Bal: ${bal:,.2f}")
    print("-" * 40)
