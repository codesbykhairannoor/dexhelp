import os
import sys
import time
import sqlite3
import requests
from dotenv import load_dotenv

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv()
BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY", "")
DB_PATH = os.path.join(os.path.dirname(__file__), "unbiased_candles.db")

def setup_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tokens (
            address TEXT PRIMARY KEY,
            symbol TEXT,
            created_at INTEGER
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS candles_1m (
            address TEXT,
            timestamp INTEGER,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            PRIMARY KEY (address, timestamp)
        )
    ''')
    conn.commit()
    return conn

def fetch_latest_profiles():
    print("🔍 [1/3] Mengambil daftar Token secara Unbiased dari Birdeye...")
    mints = []
    offsets = [0, 50, 100, 150]
    headers = {
        "X-API-KEY": BIRDEYE_API_KEY,
        "Accept": "application/json"
    }
    for off in offsets:
        # Sort by Market Cap ascending with min liquidity $1000 to get a random mix of small/new tokens
        url = f"https://public-api.birdeye.so/defi/tokenlist?sort_by=mc&sort_type=asc&offset={off}&limit=50&min_liquidity=1000"
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json().get("data", {}).get("tokens", [])
                mints.extend([t.get("address") for t in data if t.get("address")])
        except Exception as e:
            print(f"Error: {e}")
    return list(set(mints))

def fetch_creation_times(addresses):
    print("📡 [2/3] Mencari Waktu Peluncuran (Creation Time) via DexScreener...")
    batch_size = 30
    batches = [addresses[i:i + batch_size] for i in range(0, len(addresses), batch_size)]
    
    results = {}
    for batch in batches:
        addrs_str = ",".join(batch)
        url = f"https://api.dexscreener.com/latest/dex/tokens/{addrs_str}"
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                pairs = r.json().get("pairs", [])
                for pair in pairs:
                    if pair.get("chainId") != "solana":
                        continue
                    if pair.get("dexId") == "pumpfun": # Skip pump.fun curve
                        continue
                        
                    base_addr = pair.get("baseToken", {}).get("address")
                    created_at = pair.get("pairCreatedAt", 0)
                    if base_addr and created_at > 0:
                        if base_addr not in results or created_at < results[base_addr]["created_at"]:
                            results[base_addr] = {
                                "symbol": pair.get("baseToken", {}).get("symbol", "UNKNOWN"),
                                "created_at": int(created_at / 1000)
                            }
        except Exception as e:
            print(f"Error: {e}")
    return results

def fetch_historical_candles(address, time_from, time_to):
    url = f"https://public-api.birdeye.so/defi/history_price?address={address}&address_type=token&type=1m&time_from={time_from}&time_to={time_to}"
    headers = {
        "X-API-KEY": BIRDEYE_API_KEY,
        "Accept": "application/json"
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            res = r.json()
            if res.get("success"):
                return res.get("data", {}).get("items", [])
    except Exception as e:
        print(f"   [ERROR] Birdeye History error: {e}")
    return []

def main():
    print("=" * 80)
    print("🚜 UNBIASED HARVESTER: Memanen Data Murni Koin Baru (2 Jam Pertama)")
    print("=" * 80)
    
    conn = setup_db()
    c = conn.cursor()
    
    addresses = fetch_latest_profiles()
    if not addresses:
        print("Gagal mendapat token profiles.")
        return
        
    print(f"Berhasil mendapat {len(addresses)} token baru.")
    
    metadata = fetch_creation_times(addresses)
    print(f"Berhasil mendapat Waktu Peluncuran untuk {len(metadata)} token.")
    
    print("\n⏳ [3/3] Mengunduh riwayat 2 jam pertama dari masing-masing token...")
    
    count_saved = 0
    for idx, (addr, meta) in enumerate(metadata.items()):
        symbol = meta["symbol"]
        created_at = meta["created_at"]
        
        # We only care if it's older than 2 hours so we can get a full 2-hour window
        current_time = int(time.time())
        if current_time - created_at < 7200:
            print(f"[{idx+1}/{len(metadata)}] ⏭️ {symbol} (Terlalu baru, belum 2 jam)")
            continue
            
        c.execute("INSERT OR IGNORE INTO tokens (address, symbol, created_at) VALUES (?, ?, ?)", 
                  (addr, symbol, created_at))
                  
        time_to = created_at + 7200 # First 2 hours only!
        
        print(f"[{idx+1}/{len(metadata)}] ⬇️ {symbol} (Mengunduh 120 menit pertama)...")
        candles = fetch_historical_candles(addr, created_at, time_to)
        
        if candles:
            rows = []
            for item in candles:
                val = float(item.get("value", 0))
                rows.append((
                    addr,
                    int(item.get("unixTime", 0)),
                    val, val, val, val, 0.0 # using value for OHLC since /history_price
                ))
            
            c.executemany('''
                INSERT OR IGNORE INTO candles_1m (address, timestamp, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', rows)
            conn.commit()
            print(f"   ✅ Tersimpan {len(rows)} baris data untuk {symbol}.")
            count_saved += 1
        else:
            print(f"   ⚠️ Kosong.")
            
        time.sleep(0.5)
        
    print("=" * 80)
    print(f"🎉 SUKSES! {count_saved} Token Unbiased tersimpan di unbiased_candles.db")
    print("=" * 80)

if __name__ == "__main__":
    main()
