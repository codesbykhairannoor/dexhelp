import os
import sys
import sqlite3
import pandas as pd
import requests
from dotenv import load_dotenv

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv()
BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY", "")
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend", "unbiased_candles.db")

def get_token_security(address):
    url = f"https://public-api.birdeye.so/defi/token_security?address={address}"
    headers = {"X-API-KEY": BIRDEYE_API_KEY, "Accept": "application/json"}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            return r.json().get("data", {})
    except Exception:
        pass
    return {}

def get_token_overview(address):
    url = f"https://public-api.birdeye.so/defi/token_overview?address={address}"
    headers = {"X-API-KEY": BIRDEYE_API_KEY, "Accept": "application/json"}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            return r.json().get("data", {})
    except Exception:
        pass
    return {}

def main():
    print("=" * 100)
    print("🔍 MOONSHOT PROFILER: Mencari Pola Keamanan Smart Contract")
    print("=" * 100)
    
    conn = sqlite3.connect(DB_PATH)
    tokens_df = pd.read_sql_query("SELECT * FROM tokens", conn)
    
    results = []
    
    for _, row in tokens_df.iterrows():
        addr = row['address']
        symbol = row['symbol']
        candles = pd.read_sql_query("SELECT * FROM candles_1m WHERE address = ? ORDER BY timestamp ASC", conn, params=(addr,))
        candles = candles[candles['open'] > 0].reset_index(drop=True)
        
        if len(candles) < 10:
            continue
            
        open_price = candles.iloc[0]['open']
        entry_price = candles.iloc[4]['close']
        peak_price = candles['high'].max()
        gain = ((peak_price - entry_price) / entry_price) * 100
        p_change_5m = ((entry_price - open_price) / open_price) * 100
        
        sec = get_token_security(addr)
        ov = get_token_overview(addr)
        
        # Extract fields securely
        top_10 = sec.get("top10HolderPercent", 0) or 0
        mint_ren = str(sec.get("mintAuthority", "")) == "None" or not sec.get("mintAuthority")
        freeze_ren = str(sec.get("freezeAuthority", "")) == "None" or not sec.get("freezeAuthority")
        liq = ov.get("liquidity", 0) or 0
        mc = ov.get("mc", 0) or 0
        liq_mc_ratio = (liq / mc * 100) if mc > 0 else 0
        
        category = "MOONSHOT🚀" if gain >= 100.0 else "DUMP 💥" if gain < 20.0 else "SCALP 💵"
        
        results.append({
            "symbol": symbol,
            "category": category,
            "gain": gain,
            "p5m": p_change_5m,
            "top10": top_10 * 100, # Convert decimals if needed, assume it's decimal
            "mint": "YES" if mint_ren else "NO",
            "freeze": "YES" if freeze_ren else "NO",
            "liq_mc": liq_mc_ratio
        })
        
    print(f"{'SYMBOL':<10} | {'CATEGORY':<10} | {'PEAK GAIN':>10} | {'5m VEL':>8} | {'TOP10%':>8} | {'MINT_REN':>8} | {'FREEZE_REN':>10} | {'LIQ/MC%':>8}")
    print("-" * 100)
    for r in sorted(results, key=lambda x: x["gain"], reverse=True):
        print(f"{r['symbol']:<10} | {r['category']:<10} | {r['gain']:>9.1f}% | {r['p5m']:>7.1f}% | {r['top10']:>7.1f}% | {r['mint']:>8} | {r['freeze']:>10} | {r['liq_mc']:>7.1f}%")

if __name__ == "__main__":
    main()
