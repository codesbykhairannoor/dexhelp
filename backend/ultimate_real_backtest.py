import os
import sys
import sqlite3
import pandas as pd

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

DB_PATH = os.path.join(os.path.dirname(__file__), "unbiased_candles.db")

def simulate_strategy(candles, entry_price, strategy_type):
    highest_price = entry_price
    for i in range(5, len(candles)):
        current_price = candles.iloc[i]['close']
        highest_price = max(highest_price, current_price)
        gain_pct = ((highest_price - entry_price) / entry_price) * 100
        
        if strategy_type == "V1_OPTIMIZED":
            # Fixed 25% SL, BE-LOCK +5%
            if gain_pct >= 150.0:
                sl_price = highest_price * 0.75
            elif gain_pct >= 60.0:
                sl_price = highest_price * 0.80
            elif gain_pct >= 20.0:
                sl_price = entry_price * 1.05
            else:
                sl_price = entry_price * 0.75
        
        elif strategy_type == "V2_INFINITE":
            # Multi-stage Infinite Moonshot
            if gain_pct >= 300.0:
                sl_price = highest_price * 0.60
            elif gain_pct >= 100.0:
                sl_price = highest_price * 0.70
            elif gain_pct >= 50.0:
                sl_price = entry_price * 1.35
            elif gain_pct >= 20.0:
                sl_price = entry_price * 1.10
            elif gain_pct >= 4.0:
                sl_price = entry_price * 1.03
            else:
                sl_price = highest_price * 0.80
                
        elif strategy_type == "V3_STRICT_SCALP":
            # Scalper: Flat TP 30%, tight SL
            if gain_pct >= 30.0:
                return current_price, "TP_HIT"
            if gain_pct >= 10.0:
                sl_price = entry_price * 1.03
            else:
                sl_price = highest_price * 0.85 # 15% SL
                
        if current_price <= sl_price:
            return current_price, "SL_HIT"
            
    return current_price, "END_OF_DATA"

def main():
    print("=" * 80)
    print("🧪 ULTIMATE REAL BACKTEST: Mencari Holy Grail pada Data Murni")
    print("=" * 80)
    
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database {DB_PATH} tidak ditemukan.")
        return
        
    conn = sqlite3.connect(DB_PATH)
    tokens_df = pd.read_sql_query("SELECT * FROM tokens", conn)
    
    if len(tokens_df) == 0:
        print("Belum ada data di database.")
        return
        
    print(f"Menguji {len(tokens_df)} Unbiased Token (100% Real, bukan cuma top trending).")
    
    strategies = ["V1_OPTIMIZED", "V2_INFINITE", "V3_STRICT_SCALP"]
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
        
        # ENTRY SENSOR (Anti-Dump 5m)
        if price_change_5m < -2.0:
            continue
            
        entry_price = entry_candle['close']
        trade_alloc = 20.0
        
        for strategy in strategies:
            exit_price, reason = simulate_strategy(candles, entry_price, strategy)
            
            # Slippage & Fees 1% bolak-balik
            qty = (trade_alloc * 0.99) / entry_price
            net_exit = (qty * exit_price) * 0.99
            
            pnl_usd = net_exit - trade_alloc
            results[strategy]["trades"] += 1
            results[strategy]["pnl"] += pnl_usd
            if pnl_usd >= 0:
                results[strategy]["wins"] += 1
            else:
                results[strategy]["losses"] += 1

    print("\n📊 HASIL PERTANDINGAN STRATEGI:")
    for strategy in strategies:
        r = results[strategy]
        if r["trades"] == 0:
            print(f"[{strategy}] Tidak ada trade.")
            continue
        wr = (r["wins"] / r["trades"]) * 100
        print(f"\n🚀 STRATEGI: {strategy}")
        print(f"   Win Rate    : {wr:.1f}% ({r['wins']} Menang / {r['losses']} Kalah)")
        print(f"   Net PnL     : ${r['pnl']:+.2f} USD")
        print(f"   Avg per Trade: ${r['pnl']/r['trades']:+.2f} USD")
        if wr > 65.0 and r["pnl"] > 0:
            print("   🌟 HOLY GRAIL FOUND! 🌟")

if __name__ == "__main__":
    main()
