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

def simulate_strategy(candles, entry_price, strategy_type):
    highest_price = entry_price
    for i in range(5, len(candles)):
        current_price = candles.iloc[i]['close']
        highest_price = max(highest_price, current_price)
        gain_pct = ((highest_price - entry_price) / entry_price) * 100
        
        if strategy_type == "V3_STRICT_SCALP":
            if gain_pct >= 30.0:
                return current_price, "TP_HIT"
            if gain_pct >= 10.0:
                sl_price = entry_price * 1.03
            else:
                sl_price = highest_price * 0.85
                
        elif strategy_type == "V4_DIAMOND_HANDS":
            # Hold tightly until 150% profit. Stop loss is extremely wide (-40%)
            # Only trailing stop after 150%
            if gain_pct >= 300.0:
                sl_price = highest_price * 0.70
            elif gain_pct >= 150.0:
                sl_price = highest_price * 0.80
            elif gain_pct >= 80.0:
                sl_price = entry_price * 1.05 # Lock Break even at 80% gain
            else:
                sl_price = entry_price * 0.60 # -40% SL (No trailing until 80% gain)
                
        if current_price <= sl_price:
            return current_price, "SL_HIT"
            
    return current_price, "END_OF_DATA"

def main():
    conn = sqlite3.connect(DB_PATH)
    tokens_df = pd.read_sql_query("SELECT * FROM tokens", conn)
    strategies = ["V3_STRICT_SCALP", "V4_DIAMOND_HANDS"]
    results = {s: {"wins": 0, "losses": 0, "pnl": 0.0, "trades": 0} for s in strategies}
    
    for idx, row in tokens_df.iterrows():
        addr = row['address']
        candles = pd.read_sql_query("SELECT * FROM candles_1m WHERE address = ? ORDER BY timestamp ASC", conn, params=(addr,))
        candles = candles[candles['open'] > 0].reset_index(drop=True)
        
        if len(candles) < 10:
            continue
            
        entry_candle = candles.iloc[4]
        open_price = candles.iloc[0]['open']
        price_change_5m = ((entry_candle['close'] - open_price) / open_price) * 100
        
        # We learned that buying a -90% dump is too risky and buying > 45% is FOMO. 
        # So we restrict entry!
        if price_change_5m < -10.0 or price_change_5m > 40.0:
            continue
            
        entry_price = entry_candle['close']
        trade_alloc = 20.0
        
        for strategy in strategies:
            exit_price, reason = simulate_strategy(candles, entry_price, strategy)
            qty = (trade_alloc * 0.99) / entry_price
            net_exit = (qty * exit_price) * 0.99
            
            pnl_usd = net_exit - trade_alloc
            results[strategy]["trades"] += 1
            results[strategy]["pnl"] += pnl_usd
            if pnl_usd >= 0:
                results[strategy]["wins"] += 1
            else:
                results[strategy]["losses"] += 1

    for strategy in strategies:
        r = results[strategy]
        if r["trades"] == 0: continue
        wr = (r["wins"] / r["trades"]) * 100
        print(f"\n🚀 {strategy}")
        print(f"   Win Rate    : {wr:.1f}% ({r['wins']}W / {r['losses']}L)")
        print(f"   Net PnL     : ${r['pnl']:+.2f}")
        print(f"   Avg per Trade: ${r['pnl']/r['trades']:+.2f}")

if __name__ == "__main__":
    main()
