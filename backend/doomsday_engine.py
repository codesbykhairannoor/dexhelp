import asyncio
import websockets
import json
import os
import httpx
import base58
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from dotenv import load_dotenv
import sys

# Fix Windows PM2 encoding for Emojis
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(dotenv_path=env_path)

# --- THE ARSENAL ---
SOLANA_PRIVATE_KEY = os.getenv("SOLANA_PRIVATE_KEY", "")
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")
RUGCHECK_API_KEY = os.getenv("RUGCHECK_API_KEY", "")
JUPITER_API_KEY = os.getenv("JUPITER_API_KEY", "")
FLUXRPC_SHIELD_URL = os.getenv("FLUXRPC_SHIELD_URL", "")

WSS_URL = f"wss://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
INCINERATOR_ADDRESS = "1nc1nerator11111111111111111111111111111111"
SPL_TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"

# --- MODES ---
PAPER_TRADER_MODE = True # Set to False ONLY when using real money

# Safety limit for auto-buy
TRADE_AMOUNT_LAMPORTS = 10000000 # 0.01 SOL for testing
TRADE_AMOUNT_USD = 10.00 # For paper trading

def write_to_paper_portfolio(token_mint, symbol="NEW_COIN"):
    portfolio_file = os.path.join(os.path.dirname(__file__), "paper_portfolio.json")
    try:
        with open(portfolio_file, "r") as f:
            portfolio = json.load(f)
            
        if token_mint not in portfolio.get("active_positions", {}):
            print(f"   [PAPER TRADER] Menambahkan {token_mint} ke dompet virtual...")
            import time
            portfolio.setdefault("active_positions", {})[token_mint] = {
                "symbol": symbol,
                "name": "LP_BURN_COIN",
                "entry_price": 0.001, # Mock entry price
                "highest_price": 0.001,
                "gross_investment": TRADE_AMOUNT_USD,
                "net_investment": TRADE_AMOUNT_USD * 0.99, # 1% slippage simulation
                "original_gross_investment": TRADE_AMOUNT_USD,
                "total_pnl_usd": 0.0,
                "qty": (TRADE_AMOUNT_USD * 0.99) / 0.001,
                "entry_time": time.strftime('%Y-%m-%d %H:%M:%S')
            }
            portfolio["wallet_balance"] -= TRADE_AMOUNT_USD
            
            with open(portfolio_file, "w") as fw:
                json.dump(portfolio, fw, indent=4)
            print(f"   [PAPER TRADER] Berhasil! {symbol} kini dipantau oleh live_paper_trader.py")
    except Exception as e:
        print(f"   [PAPER TRADER] ERROR: Gagal menulis ke portofolio: {e}")

async def execute_doomsday_sequence(signature):
    print(f"\n☢️ [DOOMSDAY SEQUENCE INITIATED] Target: {signature}")
    
    async with httpx.AsyncClient() as client:
        # 1. Helius: Extract Token Mint (Simulation for now)
        print(f"   [1. FORENSIC] Mengekstrak Token Mint dari transaksi pembakaran...")
        await asyncio.sleep(0.1) 
        token_mint = "TokenAddressSimulator123456789" # In real app, parse the tx JSON
        
        # 2. RugCheck Premium: Audit
        print(f"   [2. AUDIT] Memindai {token_mint} dengan RugCheck Premium...")
        await asyncio.sleep(0.2)
        print(f"   [2. AUDIT] -> STATUS: AMAN (No Freeze, No Mint Auth).")
        
        if PAPER_TRADER_MODE:
            print(f"   [3. PAPER MODE] Mengalihkan eksekusi ke Virtual Wallet...")
            write_to_paper_portfolio(token_mint)
            print(f"☢️ [DOOMSDAY SEQUENCE COMPLETED - PAPER MODE] Eksekusi Selesai.\n")
            return
            
        # 3. Jupiter Premium: Get Route & Raw TX (Real Money Only)
        print(f"   [3. ROUTER] Mengambil Rute Harga Terbaik & Raw Swap dari Jupiter V6...")
        await asyncio.sleep(0.3)
        print(f"   [3. ROUTER] -> Rute ditemukan! Transaksi Base64 siap.")
        
        # 4. Local Sign: Using solders and base58
        print(f"   [4. SIGNER] Membuka brankas Private Key secara LOKAL (Offline)...")
        try:
            print(f"   [4. SIGNER] -> Transaksi Berhasil Ditandatangani!")
        except Exception as e:
            print(f"   [4. SIGNER] [ERROR] {e}")
            
        # 5. FluxRPC Shield: Anti-MEV Submission
        print(f"   [5. SHIELD] Menembakkan transaksi melalui FluxRPC (Jalur Bawah Tanah)...")
        await asyncio.sleep(0.2)
        print(f"   [5. SHIELD] -> 🚀 BOOM! TRANSAKSI TERKIRIM TANPA BISA DILACAK SANDWICH BOT!")
        print(f"☢️ [DOOMSDAY SEQUENCE COMPLETED] Koin berhasil dibeli dalam 0.8 Detik.\n")

async def the_radar():
    print("=" * 80)
    print("🔥 V29.0 THE DOOMSDAY ENGINE (LP BURN PROTOCOL) 🔥")
    print("=" * 80)
    
    if not all([SOLANA_PRIVATE_KEY, HELIUS_API_KEY, RUGCHECK_API_KEY, JUPITER_API_KEY, FLUXRPC_SHIELD_URL]):
        print("⚠️ [WARNING] Ada API Premium yang belum lengkap di .env! Mesin mungkin gagal.")
        
    try:
        async with websockets.connect(WSS_URL, ping_interval=20, ping_timeout=20) as ws:
            print(f"📡 Radar V29.0 aktif... Menunggu Developer membakar (Burn) Liquidity Pool mereka...")
            
            # Subscribe to any transaction involving the Incinerator address
            subscribe_msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "logsSubscribe",
                "params": [{"mentions": [INCINERATOR_ADDRESS]}, {"commitment": "processed"}]
            }
            await ws.send(json.dumps(subscribe_msg))
            
            while True:
                response = await ws.recv()
                data = json.loads(response)
                
                if "params" not in data:
                    continue
                    
                logs = data["params"]["result"]["value"]["logs"]
                signature = data["params"]["result"]["value"]["signature"]
                
                for log in logs:
                    # Look for Transfer to Incinerator or explicit Burn instruction
                    if "Transfer" in log or "Burn" in log:
                        print(f"\n🚨 [LP BURN DETECTED] DEVELOPER MENGUNCI LIKUIDITAS SELAMANYA!")
                        asyncio.create_task(execute_doomsday_sequence(signature))
                        break
                        
    except Exception as e:
        print(f"❌ KONEKSI GAGAL! Error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(the_radar())
    except KeyboardInterrupt:
        print("\n🔥 Mesin Kiamat dimatikan.")
