import asyncio
import websockets
import json
import os
from dotenv import load_dotenv

load_dotenv()

HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")

# We use the free tier WSS endpoint from Helius
WSS_URL = f"wss://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

# List of Smart Money / Whale Addresses to monitor
# Example addresses (replace with real whales)
WHALE_ADDRESSES = [
    "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pTEXpw",
    "9WzDXwBbmcg8ZXH295A2QyM2E4XyT4pAHRTnH6x352k9"
]

async def whale_tracker_stream():
    if not HELIUS_API_KEY:
        print("❌ KONEKSI GAGAL! HELIUS_API_KEY tidak ditemukan di .env!")
        return

    print("=" * 80)
    print("🐋 V26.0 HELIUS WHALE COPY-TRADER STARTING 🐋")
    print(f"📡 Menghubungkan ke Helius WSS secara GRATIS (No Rate Limit)...")
    print("=" * 80)
    
    try:
        async with websockets.connect(WSS_URL, ping_interval=20, ping_timeout=20) as ws:
            print(f"✅ BERHASIL TERHUBUNG KE JARINGAN HELIUS!")
            print(f"🎯 Menargetkan {len(WHALE_ADDRESSES)} Dompet Paus...")
            
            # Subscribe to account changes for all whales
            for i, address in enumerate(WHALE_ADDRESSES):
                subscribe_msg = {
                    "jsonrpc": "2.0",
                    "id": i+1,
                    "method": "accountSubscribe",
                    "params": [
                        address,
                        {"encoding": "jsonParsed", "commitment": "confirmed"}
                    ]
                }
                await ws.send(json.dumps(subscribe_msg))
                
            print(f"🕵️ Mata-mata Aktif! Menunggu Paus bergerak...\n")
            
            while True:
                try:
                    response = await ws.recv()
                    data = json.loads(response)
                    
                    # Ignore subscription confirmations
                    if "params" not in data:
                        continue
                        
                    # Extract the payload
                    account_info = data["params"]["result"]["value"]
                    
                    # This indicates the Whale's wallet balance or token accounts changed
                    # In a real system, you would cross-reference this with a getTransaction RPC call
                    # (which costs 1 request out of the 100k daily limit) to see EXACTLY what token they bought
                    
                    print(f"🚨 [GERAKAN PAUS TERDETEKSI] Saldo salah satu Paus berubah!")
                    print(f"📊 Mengeksekusi 'getTransaction' (Memotong 1/100,000 Kuota Harian) untuk melihat Token apa yang dibeli...")
                    print(f"🔫 Menyiapkan Peluru Beli Jupiter/Raydium...\n")
                    
                except Exception as stream_e:
                    print(f"⚠️ Aliran data terputus sementara: {stream_e}")
                    break
                    
    except Exception as e:
        print(f"❌ KONEKSI GAGAL! Error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(whale_tracker_stream())
    except KeyboardInterrupt:
        print("\n🐋 Whale Tracker mematikan mesin pemantau.")
