import os
import sys
import sqlite3
import pandas as pd

# Fix Windows terminal encoding for Emojis
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

DB_PATH = os.path.join(os.path.dirname(__file__), "historical_candles.db")

def main():
    print("=" * 80)
    print("🤖 TRUE HISTORICAL BACKTEST: Simulasi Realita Tanpa RNG")
    print("=" * 80)
    
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database {DB_PATH} tidak ditemukan.")
        return
        
    conn = sqlite3.connect(DB_PATH)
    tokens_df = pd.read_sql_query("SELECT * FROM tokens", conn)
    
    initial_capital = 1000.0
    wallet_balance = initial_capital
    trade_allocation = 10.0
    
    total_trades = 0
    wins = 0
    losses = 0
    
    print(f"[INFO] Modal Awal: ${wallet_balance:.2f} | Alokasi per Trade: ${trade_allocation:.2f}")
    print("[INFO] Strategi: OPTIMIZED (Fixed 25% SL Awal -> Trail TP)\n")
    
    for idx, row in tokens_df.iterrows():
        addr = row['address']
        symbol = row['symbol']
        
        candles = pd.read_sql_query("SELECT * FROM candles_1m WHERE address = ? ORDER BY timestamp ASC", conn, params=(addr,))
        candles = candles[candles['open'] > 0].reset_index(drop=True)
        
        if len(candles) < 10:
            continue
            
        # --- ENTRY SIMULATION ---
        # Assume we enter at the end of the 5th minute if it hasn't dumped.
        # This simulates the "delay" of finding it on DexScreener.
        entry_candle = candles.iloc[4]
        open_price = candles.iloc[0]['open']
        price_change_5m = ((entry_candle['close'] - open_price) / open_price) * 100
        
        # Apply our new Anomaly Filter: Do not buy if 5m price dropped below -2.0%
        if price_change_5m < -2.0:
            # print(f"🚫 [FILTERED] {symbol} dihindari karena Velocity 5m negatif ({price_change_5m:.2f}%)")
            continue
            
        # Entry execution
        entry_price = entry_candle['close']
        
        # 1% slippage + swap fees
        net_investment = trade_allocation * 0.99 
        qty = net_investment / entry_price
        
        wallet_balance -= trade_allocation
        total_trades += 1
        
        highest_price = entry_price
        exit_price = 0.0
        trail_level = ""
        
        # --- HOLD SIMULATION ---
        for i in range(5, len(candles)):
            c_row = candles.iloc[i]
            current_price = c_row['close']
            highest_price = max(highest_price, current_price)
            
            price_gain_pct = ((highest_price - entry_price) / entry_price) * 100
            
            # OPTIMIZED Logic (Mirrors live_paper_trader.py fix)
            if price_gain_pct >= 150.0:
                sl_price = highest_price * 0.75  # Trail 25% from peak
                trail_level = "STAGE 3 (25% TSL)"
            elif price_gain_pct >= 60.0:
                sl_price = highest_price * 0.80  # Trail 20% from peak
                trail_level = "STAGE 2 (20% TSL)"
            elif price_gain_pct >= 20.0:
                sl_price = entry_price * 1.02  # Lock +2% profit when hit +20%
                trail_level = "BE-LOCK (+2%)"
            else:
                sl_price = entry_price * 0.75  # Fixed 25% Initial SL
                trail_level = "OPTIMIZED INITIAL SL (25%)"
                
            if current_price <= sl_price:
                exit_price = current_price
                break
        else:
            # Reached end of history without hitting SL
            exit_price = current_price
            trail_level = "END_OF_DATA"
            
        # Exit execution
        net_exit_value = qty * exit_price
        # 1% slippage + swap fees on exit
        net_exit_value *= 0.99 
        
        pnl_usd = net_exit_value - trade_allocation
        realized_pnl_pct = (pnl_usd / trade_allocation) * 100
        
        wallet_balance += net_exit_value
        
        if pnl_usd >= 0:
            wins += 1
            status = "WIN "
        else:
            losses += 1
            status = "LOSS"
            
        print(f"[{status}] {symbol:<10} | In: ${entry_price:.6f} | Out: ${exit_price:.6f} | PnL: {realized_pnl_pct:>+7.2f}% | Guard: {trail_level}")

    print("\n" + "=" * 80)
    print("🏆 HASIL AKHIR: TRUE HISTORICAL BACKTEST")
    print("=" * 80)
    print(f"  Total Trades        : {total_trades}")
    if total_trades > 0:
        print(f"  Real Win Rate       : {(wins / total_trades) * 100:.1f}%")
    print(f"  Saldo Akhir         : ${wallet_balance:.2f} (Modal: ${initial_capital:.2f})")
    print(f"  Net PnL             : {((wallet_balance - initial_capital) / initial_capital) * 100:+.2f}%")
    print("=" * 80)

if __name__ == "__main__":
    main()
