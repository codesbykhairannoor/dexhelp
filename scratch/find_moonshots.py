import sqlite3
import pandas as pd
import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def analyze_db(db_name):
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend", db_name)
    if not os.path.exists(db_path):
        print(f"DB {db_name} not found.")
        return
        
    conn = sqlite3.connect(db_path)
    try:
        tokens_df = pd.read_sql_query("SELECT * FROM tokens", conn)
    except Exception as e:
        print(f"Error reading tokens from {db_name}: {e}")
        return
        
    print(f"\n[{db_name}] Analyzing {len(tokens_df)} tokens for MOONSHOTS (>100% peak gain)")
    
    moonshots = []
    
    for _, row in tokens_df.iterrows():
        addr = row['address']
        symbol = row['symbol']
        candles = pd.read_sql_query("SELECT * FROM candles_1m WHERE address = ? ORDER BY timestamp ASC", conn, params=(addr,))
        candles = candles[candles['open'] > 0].reset_index(drop=True)
        
        if len(candles) < 10:
            continue
            
        open_price = candles.iloc[0]['open']
        entry_price = candles.iloc[4]['close'] # Buy at minute 5
        
        peak_price = candles['high'].max()
        gain_from_entry = ((peak_price - entry_price) / entry_price) * 100
        
        if gain_from_entry >= 100.0:
            # IT'S A MOONSHOT!
            # Gather 5m stats
            c_0 = candles.iloc[0]
            c_4 = candles.iloc[4]
            p_change_5m = ((c_4['close'] - c_0['open']) / c_0['open']) * 100
            v_5m = candles.iloc[0:5]['volume'].sum()
            
            moonshots.append({
                "symbol": symbol,
                "gain": gain_from_entry,
                "p_change_5m": p_change_5m,
                "vol_5m": v_5m
            })
            
    if moonshots:
        for m in sorted(moonshots, key=lambda x: x["gain"], reverse=True):
            print(f"🚀 {m['symbol']:<10} | Peak Gain: {m['gain']:>6.1f}% | 5m Velocity: {m['p_change_5m']:>+6.1f}% | 5m Vol: {m['vol_5m']:,.0f}")
    else:
        print("😭 No moonshots found in this DB.")

analyze_db("historical_candles.db")
analyze_db("unbiased_candles.db")
