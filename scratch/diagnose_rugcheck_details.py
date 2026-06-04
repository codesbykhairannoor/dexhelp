import requests
import time
import sys

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Import the exact logic from dex_hunter to simulate it
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from dex_hunter import check_token_security, calculate_gem_score
from config import MIN_LIQ, MAX_LIQ, MIN_MCAP, MIN_VOL_5M, MIN_TRADES_5M, MAX_AGE_MINUTES

def run_diagnostics():
    print("================================================================================")
    print("🔬 GILA-GILAAN BACKTEST: ZERO-MINUTE SNIPE DIAGNOSTICS")
    print("================================================================================")
    
    print(f"Filter Aktif: Max Age: {MAX_AGE_MINUTES}m | Min Liq: ${MIN_LIQ} | Min Vol: ${MIN_VOL_5M} | Min Trades: {MIN_TRADES_5M}")
    
    try:
        r_new = requests.get('https://api.rugcheck.xyz/v1/stats/new_tokens', timeout=5)
        if r_new.status_code != 200:
            print("Gagal akses RugCheck")
            return
            
        mints = []
        for t in r_new.json():
            if t.get('mint'): mints.append(t.get('mint'))
            
        mints = mints[:30] # Top 30 newest
        mints_str = ",".join(mints)
        
        ds_r = requests.get(f'https://api.dexscreener.com/latest/dex/tokens/{mints_str}', timeout=10)
        pairs = ds_r.json().get('pairs', [])
        
        print(f"\nMenganalisa {len(pairs)} pasangan trading yang baru lahir...\n")
        
        passed_filter_count = 0
        
        for pair in pairs:
            if pair.get('chainId') != 'solana': continue
            if pair.get('dexId') == 'pumpfun': continue
            
            mint = pair.get('baseToken', {}).get('address')
            symbol = pair.get('baseToken', {}).get('symbol', 'UNKNOWN')
            
            liq = float(pair.get('liquidity', {}).get('usd', 0) or 0)
            v5m = float(pair.get('volume', {}).get('m5', 0) or 0)
            buys = int(pair.get('txns', {}).get('m5', {}).get('buys', 0) or 0)
            sells = int(pair.get('txns', {}).get('m5', {}).get('sells', 0) or 0)
            trades = buys + sells
            
            pair_created_at = pair.get('pairCreatedAt', 0)
            age_min = max(0.0, (time.time() * 1000.0 - pair_created_at) / 60000.0) if pair_created_at > 0 else 60.0
            
            # Simulate Filters
            print(f"Token: {symbol}")
            print(f"  └ Umur: {age_min:.1f}m | Liq: ${liq:.0f} | Vol5m: ${v5m:.0f} | Trades: {trades} ({buys}/{sells})")
            
            if age_min > MAX_AGE_MINUTES:
                print("  => ❌ [REJECT] Umur Terlalu Tua")
                continue
            if liq < MIN_LIQ or liq > MAX_LIQ:
                print("  => ❌ [REJECT] Likuiditas Tidak Sesuai")
                continue
            if trades < MIN_TRADES_5M or v5m < MIN_VOL_5M:
                print("  => ❌ [REJECT] Aktivitas (Vol/Trades) Terlalu Rendah")
                continue
            if buys < 15 or buys <= (sells * 2.0):
                print("  => ❌ [REJECT] Rasio Pembeli Lemah")
                continue
                
            passed_filter_count += 1
            print("  => ✅ Lolos Filter DexScreener. Menguji RugCheck...")
            
            # Simulate Score
            c = {
                "address": mint,
                "symbol": symbol,
                "name": pair.get('baseToken', {}).get('name', ''),
                "liquidity": liq,
                "volume_5m": v5m,
                "volume_1h": float(pair.get('volume', {}).get('h1', 0) or 0),
                "volume_24h": float(pair.get('volume', {}).get('h24', 0) or 0),
                "price_change_5m": float(pair.get('priceChange', {}).get('m5', 0) or 0),
                "price_change_1h": float(pair.get('priceChange', {}).get('h1', 0) or 0),
                "market_cap": float(pair.get('marketCap', 0) or 0),
                "age_estimate_sec": age_min * 60,
                "zero_minute_snipe": age_min < 5.0,
                "txns": pair.get('txns', {})
            }
            
            sec = check_token_security("solana", mint)
            print(f"  => RugCheck Status: {sec['status']} | Flags: {sec['flags']}")
            
            score = calculate_gem_score(c, sec)
            print(f"  => FINAL SCORE: {score}/100")
            
            if score >= 80:
                print("  => 🚀🚀🚀 KOIN INI AKAN DIBELI OLEH BOT! 🚀🚀🚀")
            else:
                print("  => ❌ [REJECT] Skor di bawah 80")
                
        print(f"\nKesimpulan: Dari {len(pairs)} token, {passed_filter_count} lolos filter awal.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_diagnostics()
