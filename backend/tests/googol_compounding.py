import sys
import random

# Fix Windows terminal encoding for Emojis
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def run_googol_simulation(initial_capital: float = 12.0, trade_margin_pct: float = 0.40):
    """
    Simulates a compounding portfolio starting with $12.00 and compounding 40% margin per trade,
    running day-by-day until the wallet balance reaches 1 Googol Dollars (10^100).
    """
    random.seed(999) # For reproducible simulation path
    
    current_wallet = initial_capital
    target_googol = 10**100
    trailing_sl_pct = 0.20
    
    # Transaction costs per trade
    gas_fee = 0.12
    swap_fee_pct = 0.01
    slippage_pct = 0.02
    
    trades_executed = 0
    day = 1
    
    print("=" * 80)
    print("🛸 GOOGOL COMPOUNDING SIMULATOR - DAY-BY-DAY PROGRESSION")
    print(f"💰 Starting Capital : ${initial_capital:.2f}")
    print(f"💼 Trade Allocation  : {trade_margin_pct * 100:.0f}% of Compounding Capital")
    print(f"🎯 Target Capital    : 1 Googol USD ($1.00 x 10^100)")
    print("=" * 80)
    
    # We will log the day-by-day balance at the end of each day
    day_logs = []
    
    # Run the compounding cycles day-by-day
    while current_wallet < target_googol:
        # Memecoins have active days and slow days.
        # Average 3 trades per day
        day_trades = random.choices([1, 2, 3, 4, 5], weights=[0.1, 0.2, 0.4, 0.2, 0.1])[0]
        
        day_wins = 0
        day_losses = 0
        day_start_balance = current_wallet
        
        for _ in range(day_trades):
            trades_executed += 1
            trade_allocation = current_wallet * trade_margin_pct
            cost_per_trade = gas_fee + (trade_allocation * swap_fee_pct) + (trade_allocation * slippage_pct)
            net_entry = trade_allocation - cost_per_trade
            
            # Outcome path simulation (ScamShield V4: 8% Dump, 52% Scalp, 40% Moonshot)
            category = random.choices(["DUMP", "SCALP", "MOONSHOT"], weights=[0.08, 0.52, 0.40])[0]
            
            entry_price = 1.0
            highest_price = entry_price
            current_price = entry_price
            steps = 50
            exit_price = entry_price
            
            if category == "DUMP":
                for _ in range(steps):
                    current_price *= random.uniform(0.85, 1.02)
                    highest_price = max(highest_price, current_price)
                    if current_price <= highest_price * (1 - trailing_sl_pct):
                        exit_price = highest_price * (1 - trailing_sl_pct)
                        break
                else:
                    exit_price = current_price
            elif category == "SCALP":
                for step in range(steps):
                    if step < 20: current_price *= random.uniform(0.96, 1.08)
                    else: current_price *= random.uniform(0.92, 1.02)
                    highest_price = max(highest_price, current_price)
                    if current_price <= highest_price * (1 - trailing_sl_pct):
                        exit_price = highest_price * (1 - trailing_sl_pct)
                        break
                else:
                    exit_price = current_price
            else:
                for step in range(steps):
                    if step < 35: current_price *= random.uniform(0.98, 1.16)
                    else: current_price *= random.uniform(0.88, 1.02)
                    highest_price = max(highest_price, current_price)
                    if current_price <= highest_price * (1 - trailing_sl_pct):
                        exit_price = highest_price * (1 - trailing_sl_pct)
                        break
                else:
                    exit_price = current_price
            
            # PnL math
            trade_yield_pct = ((exit_price - entry_price) / entry_price) * 100
            trade_pnl = net_entry * (trade_yield_pct / 100)
            
            if trade_pnl > 0:
                day_wins += 1
            else:
                day_losses += 1
                
            current_wallet += trade_pnl
            
        # Log the end-of-day progression
        day_logs.append({
            "day": day,
            "trades": day_trades,
            "wins": day_wins,
            "losses": day_losses,
            "start": day_start_balance,
            "end": current_wallet
        })
        
        # Display the first 10 days, and then snapshots every 15 days
        if day <= 10 or day % 15 == 0:
            # Format number gracefully: scientific notation if too large
            if current_wallet > 10**6:
                balance_str = f"{current_wallet:.2e}"
            else:
                balance_str = f"${current_wallet:,.2f}"
            print(f"📅 Day {day:03d} | Start: ${day_start_balance:,.2f} | End: {balance_str} | Trades: {day_trades} ({day_wins}W - {day_losses}L)")
            
        day += 1
        
    print("-" * 80)
    print("🏆 TARGET ACHIEVED! 1 GOOGOL USD EXCEEDED!")
    print("-" * 80)
    print(f"  ⏱️ Total Duration Required: {day - 1} Days (Sekitar {(day - 1)/30:.1f} Bulan!)")
    print(f"  🔄 Total Trades Executed   : {trades_executed} Trades")
    print(f"  💵 Final Wallet Balance    : {current_wallet:.4e} USD")
    print("=" * 80)

if __name__ == "__main__":
    run_googol_simulation()
