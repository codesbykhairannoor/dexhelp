import os
import sys
import sqlite3
import pandas as pd

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend", "unbiased_candles.db")

def simulate_strategy_v5(candles, entry_price):
    highest_price = entry_price
    partial_tp_hit = False
    
    exit_pnl_usd = 0.0
    trade_alloc = 20.0
    
    qty = (trade_alloc * 0.99) / entry_price # Initial Qty after entry fees
    rem_qty = qty
    orig_alloc = trade_alloc
    
    for i in range(5, len(candles)):
        current_price = candles.iloc[i]['close']
        highest_price = max(highest_price, current_price)
        gain_pct = ((highest_price - entry_price) / entry_price) * 100
        
        # SL logic
        if not partial_tp_hit:
            if gain_pct >= 30.0: # Trigger 80% Partial TP at +30%
                partial_tp_hit = True
                sell_qty = rem_qty * 0.80
                rem_qty -= sell_qty
                # Take 80% profit
                net_exit = (sell_qty * current_price) * 0.99
                exit_pnl_usd += net_exit - (trade_alloc * 0.80)
                continue
            
            elif gain_pct >= 10.0:
                sl_price = entry_price * 1.03
            else:
                sl_price = highest_price * 0.85
        else:
            # MOONSHOT RUNNER LOGIC (20% Bag)
            if gain_pct >= 300.0:
                sl_price = highest_price * 0.70
            elif gain_pct >= 150.0:
                sl_price = highest_price * 0.80
            elif gain_pct >= 80.0:
                sl_price = entry_price * 1.50 # Lock +50% on runner
            else:
                sl_price = entry_price * 1.03 # Lock +3% Break-even on the runner
                
        if current_price <= sl_price:
            # Exit remaining
            net_exit = (rem_qty * current_price) * 0.99
            alloc_rem = trade_alloc * 0.20 if partial_tp_hit else trade_alloc
            exit_pnl_usd += net_exit - alloc_rem
            rem_qty = 0
            break
            
    if rem_qty > 0:
        net_exit = (rem_qty * current_price) * 0.99
        alloc_rem = trade_alloc * 0.20 if partial_tp_hit else trade_alloc
        exit_pnl_usd += net_exit - alloc_rem
        
    return exit_pnl_usd, "W" if exit_pnl_usd >= 0 else "L"

def main():
    conn = sqlite3.connect(DB_PATH)
    tokens_df = pd.read_sql_query("SELECT * FROM tokens", conn)
    
    wins = 0
    losses = 0
    total_pnl = 0.0
    trades = 0
    
    for idx, row in tokens_df.iterrows():
        addr = row['address']
        candles = pd.read_sql_query("SELECT * FROM candles_1m WHERE address = ? ORDER BY timestamp ASC", conn, params=(addr,))
        candles = candles[candles['open'] > 0].reset_index(drop=True)
        
        if len(candles) < 10:
            continue
            
        entry_candle = candles.iloc[4]
        open_price = candles.iloc[0]['open']
        price_change_5m = ((entry_candle['close'] - open_price) / open_price) * 100
        
        if price_change_5m < -10.0 or price_change_5m > 40.0:
            continue
            
        entry_price = entry_candle['close']
        
        pnl, status = simulate_strategy_v5(candles, entry_price)
        trades += 1
        total_pnl += pnl
        if status == "W": wins += 1
        else: losses += 1

    if trades > 0:
        wr = (wins / trades) * 100
        print(f"\n🚀 V5_SCALP_AND_RUNNER (80% TP at 30%, 20% Moonshot)")
        print(f"   Win Rate    : {wr:.1f}% ({wins}W / {losses}L)")
        print(f"   Net PnL     : ${total_pnl:+.2f}")
        print(f"   Avg per Trade: ${total_pnl/trades:+.2f}")

if __name__ == "__main__":
    main()
