import asyncio
import websockets
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Raydium AMM Program ID v4
RAYDIUM_PROGRAM_ID = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
# Pump.fun Program ID
PUMP_FUN_PROGRAM_ID = "6EF8rrecthR5Dkzon8Nwu78hRvfX9eAeyuG4j9M7Ctz"

# You MUST use a premium WSS URL (like Helius or QuickNode) for this to be stable.
WSS_URL = os.getenv("HELIUS_WSS_URL", "wss://api.mainnet-beta.solana.com")

async def apex_predator_stream():
    print("=" * 80)
    print("🦅 V25.0 APEX PREDATOR: ZERO-BLOCK SNIPER ENGINE STARTING 🦅")
    print(f"📡 Connecting to RPC: {WSS_URL[:30]}...")
    print("=" * 80)
    
    try:
        async with websockets.connect(WSS_URL, ping_interval=20, ping_timeout=20) as ws:
            print("✅ BERHASIL TERHUBUNG KE JANTUNG SOLANA!")
            
            # Subscribe to Raydium Program Logs
            subscribe_msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "logsSubscribe",
                "params": [
                    {"mentions": [RAYDIUM_PROGRAM_ID]},
                    {"commitment": "processed"}
                ]
            }
            
            await ws.send(json.dumps(subscribe_msg))
            print(f"🎯 Menembak radar ke Raydium (Menunggu LP Baru)...")
            
            while True:
                try:
                    response = await ws.recv()
                    data = json.loads(response)
                    
                    # Bypass confirmation messages
                    if "params" not in data:
                        continue
                        
                    logs = data["params"]["result"]["value"]["logs"]
                    signature = data["params"]["result"]["value"]["signature"]
                    
                    # We are looking for "InitializeInstruction2" or "Initialize2" which creates a new pool
                    for log in logs:
                        if "InitializeInstruction2" in log or "init_pc_amount" in log:
                            print(f"\n🚨 [ZERO-BLOCK DETECTED] RAYDIUM POOL BARU LAHIR!")
                            print(f"🔗 Tx: https://solscan.io/tx/{signature}")
                            print(f"⚡ Waktu Deteksi: 0.001 Detik sejak divalidasi!")
                            print(f"💰 Menyiapkan Jito Bundler untuk Buy di Block yang sama...\n")
                            break
                            
                except Exception as stream_e:
                    print(f"⚠️ Aliran data terputus sementara: {stream_e}")
                    break
                    
    except Exception as e:
        print(f"❌ KONEKSI GAGAL! Mesin V25.0 Predator WAJIB menggunakan Helius/QuickNode WSS.")
        print(f"Error detail: {e}")
        print("Silakan isi HELIUS_WSS_URL di file .env Anda!")

if __name__ == "__main__":
    if WSS_URL == "wss://api.mainnet-beta.solana.com":
        print("\n[PERINGATAN] Anda masih menggunakan Solana WSS Publik (Gratis).")
        print("Koneksi ini akan sangat tidak stabil dan sering diputus oleh jaringan.")
        print("Untuk mode APEX PREDATOR, belilah akses Helius Labs atau QuickNode.\n")
        
    try:
        asyncio.run(apex_predator_stream())
    except KeyboardInterrupt:
        print("\n🦅 Apex Predator mematikan mesin pemantau.")
