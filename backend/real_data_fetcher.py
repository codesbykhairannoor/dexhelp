import os
import sys
import time
import json
import sqlite3
import requests
from dotenv import load_dotenv

# Fix Windows terminal encoding for Emojis
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv()

BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY", "")
DB_PATH = os.path.join(os.path.dirname(__file__), "historical_candles.db")

def setup_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Table for tokens
    c.execute('''
        CREATE TABLE IF NOT EXISTS tokens (
            address TEXT PRIMARY KEY,
            symbol TEXT,
            name TEXT,
            liquidity REAL,
            market_cap REAL,
            volume_24h REAL,
            created_at INTEGER
        )
    ''')
    # Table for 1m candles
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

def fetch_trending_tokens():
    print("🔍 Mengambil daftar token trending dari Birdeye API...")
    url = "https://public-api.birdeye.so/defi/token_trending?sort_by=rank&sort_type=asc&offset=0&limit=50"
    headers = {
        "X-API-KEY": BIRDEYE_API_KEY,
        "Accept": "application/json"
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json().get("data", {}).get("tokens", [])
            return [t for t in data if t.get("address")]
        else:
            print(f"[ERROR] API Birdeye (Trending) gagal: HTTP {r.status_code}")
            return []
    except Exception as e:
        print(f"[ERROR] Gagal mengambil token trending: {e}")
        return []

def fetch_dexscreener_info(addresses):
    print("📡 Mengambil metadata riil (Liquidity/Mcap) dari DexScreener...")
    # DexScreener allows max 30 per request
    batch_size = 30
    batches = [addresses[i:i + batch_size] for i in range(0, len(addresses), batch_size)]
    
    token_metadata = {}
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
                    base_addr = pair.get("baseToken", {}).get("address")
                    if base_addr and base_addr not in token_metadata:
                        token_metadata[base_addr] = {
                            "symbol": pair.get("baseToken", {}).get("symbol", "UNKNOWN"),
                            "name": pair.get("baseToken", {}).get("name", "UNKNOWN"),
                            "liquidity": float(pair.get("liquidity", {}).get("usd", 0) or 0),
                            "market_cap": float(pair.get("marketCap", 0) or pair.get("fdv", 0) or 0),
                            "volume_24h": float(pair.get("volume", {}).get("h24", 0) or 0),
                            "created_at": int(pair.get("pairCreatedAt", 0) / 1000)
                        }
        except Exception as e:
            print(f"[ERROR] DexScreener API error: {e}")
    return token_metadata

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
    print("⛏️ REAL DATA FETCHER: Menambang Data Historis 1-Menit Solana Memecoins")
    print("=" * 80)
    
    if not BIRDEYE_API_KEY:
        print("[ERROR] BIRDEYE_API_KEY tidak ditemukan di .env!")
        return

    conn = setup_db()
    c = conn.cursor()
    
    tokens = fetch_trending_tokens()
    if not tokens:
        print("Tidak ada token yang ditemukan. Berhenti.")
        return
        
    print(f"Ditemukan {len(tokens)} token trending potensial.")
    
    addresses = [t["address"] for t in tokens]
    metadata = fetch_dexscreener_info(addresses)
    
    time_to = int(time.time())
    time_from = time_to - (24 * 3600)  # 24 Hours ago
    
    count_saved = 0
    for idx, addr in enumerate(addresses):
        meta = metadata.get(addr)
        if not meta:
            continue
            
        # Insert token metadata
        c.execute('''
            INSERT OR IGNORE INTO tokens (address, symbol, name, liquidity, market_cap, volume_24h, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (addr, meta["symbol"], meta["name"], meta["liquidity"], meta["market_cap"], meta["volume_24h"], meta["created_at"]))
        
        print(f"[{idx+1}/{len(addresses)}] Mengunduh OHLCV 1M: {meta['symbol']} ({addr[:8]}...)")
        
        candles = fetch_historical_candles(addr, time_from, time_to)
        if candles:
            rows = []
            for item in candles:
                val = float(item.get("value", 0))
                rows.append((
                    addr,
                    int(item.get("unixTime", 0)),
                    val, val, val, val, 0.0 # open, high, low, close, volume
                ))
            
            c.executemany('''
                INSERT OR IGNORE INTO candles_1m (address, timestamp, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', rows)
            conn.commit()
            print(f"   ✅ Tersimpan {len(rows)} data candle 1-menit untuk {meta['symbol']}.")
            count_saved += 1
        else:
            print(f"   ⚠️ Tidak ada data OHLCV dari Birdeye untuk {meta['symbol']}.")
            
        time.sleep(0.5) # Pace Birdeye API limit
        
    print("=" * 80)
    print(f"🎉 SUKSES! Mengunduh data historis murni dari {count_saved} token Solana.")
    print(f"Data disimpan di: {DB_PATH}")
    print("=" * 80)

if __name__ == "__main__":
    main()
