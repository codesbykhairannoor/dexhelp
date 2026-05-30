import os
import sys
import sqlite3
import pandas as pd
import numpy as np

# Fix Windows terminal encoding for Emojis
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

DB_PATH = os.path.join(os.path.dirname(__file__), "historical_candles.db")

def main():
    print("=" * 80)
    print("🔬 SOLANA ANOMALY DETECTOR: Mencari Pola Pemenang dari Data Historis Nyata")
    print("=" * 80)
    
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database {DB_PATH} tidak ditemukan. Jalankan real_data_fetcher.py dahulu.")
        return
        
    conn = sqlite3.connect(DB_PATH)
    
    # Load tokens
    tokens_df = pd.read_sql_query("SELECT * FROM tokens", conn)
    print(f"Total token terdeteksi: {len(tokens_df)}")
    
    if len(tokens_df) == 0:
        print("Tidak ada data. Berhenti.")
        return

    results = []
    
    for idx, row in tokens_df.iterrows():
        addr = row['address']
        symbol = row['symbol']
        
        # Load candles ordered by timestamp
        candles = pd.read_sql_query("SELECT * FROM candles_1m WHERE address = ? ORDER BY timestamp ASC", conn, params=(addr,))
        
        if len(candles) < 10:
            continue
            
        candles = candles[candles['open'] > 0].reset_index(drop=True)
        if len(candles) < 10:
            continue
            
        open_price = candles.iloc[0]['open']
            
        peak_price = candles['high'].max()
        bottom_price = candles['low'].min()
        
        peak_gain_pct = ((peak_price - open_price) / open_price) * 100
        max_drawdown_pct = ((bottom_price - open_price) / open_price) * 100
        
        # Calculate metrics
        first_5m = candles.head(5)
        c_5m = first_5m.iloc[-1]['close']
        price_change_5m = ((c_5m - open_price) / open_price) * 100
        
        liq = row['liquidity']
        mcap = row['market_cap']
        liq_ratio = (liq / mcap) * 100 if mcap > 0 else 0
        
        # Determine category
        if peak_gain_pct >= 30.0:
            category = "MEGA_PUMP"
        elif max_drawdown_pct <= -20.0 and peak_gain_pct < 10.0:
            category = "DUMP"
        else:
            category = "CHOP/SCALP"
            
        results.append({
            "symbol": symbol,
            "address": addr,
            "category": category,
            "peak_gain_pct": peak_gain_pct,
            "max_drawdown_pct": max_drawdown_pct,
            "price_change_5m": price_change_5m,
            "liquidity": liq,
            "market_cap": mcap,
            "liq_ratio": liq_ratio
        })
        
    res_df = pd.DataFrame(results)
    if len(res_df) == 0:
        print("Tidak ada cukup candle untuk dianalisis.")
        return
        
    print("\n📊 DISTRIBUSI REALITA (KEMANA ARAH PASAR SEBENARNYA?):")
    counts = res_df['category'].value_counts()
    for cat, count in counts.items():
        print(f"   - {cat}: {count} token ({count/len(res_df)*100:.1f}%)")
        
    mega_pumps = res_df[res_df['category'] == 'MEGA_PUMP']
    dumps = res_df[res_df['category'] == 'DUMP']
    
    print("\n🔍 ANOMALI PENEMUAN (MEGA PUMPS vs DUMPS):")
    
    if len(mega_pumps) > 0:
        print("\n🏆 SIFAT-SIFAT MEGA PUMP (Naik >100%):")
        print(f"   - Rata-rata Kenaikan Harga di 5 Menit Pertama: {mega_pumps['price_change_5m'].mean():+.2f}%")
        print(f"   - Median Liquidity saat ini: ${mega_pumps['liquidity'].median():,.2f}")
        print(f"   - Median Ratio Liq/Mcap: {mega_pumps['liq_ratio'].median():.2f}%")
    
    if len(dumps) > 0:
        print("\n🗑️ SIFAT-SIFAT DUMPS (Rugi >50% tanpa sempat naik 20%):")
        print(f"   - Rata-rata Kenaikan Harga di 5 Menit Pertama: {dumps['price_change_5m'].mean():+.2f}%")
        print(f"   - Median Liquidity saat ini: ${dumps['liquidity'].median():,.2f}")
        print(f"   - Median Ratio Liq/Mcap: {dumps['liq_ratio'].median():.2f}%")
        
    print("\n💡 KESIMPULAN FORMULA BARU:")
    print("  Perhatikan perbedaan Liq/Mcap Ratio dan Kecepatan Kenaikan di 5 Menit Pertama.")
    print("=" * 80)
    
if __name__ == "__main__":
    main()
