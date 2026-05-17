import os
import requests
from dotenv import load_dotenv

# Load environmental variables from absolute path .env
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
env_path = os.path.join(parent_dir, '.env')
load_dotenv(env_path)

def check_live_balance():
    helius_url = os.getenv("SOLANA_RPC_HELIUS")
    wallet_address = "DztA69g7N88qxZ65zL2k5xFKqdwiRCrTyYy6zLMrqkYt"
    
    if not helius_url:
        print("ERROR: Helius RPC URL is missing in .env")
        return
        
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getBalance",
        "params": [wallet_address]
    }
    
    try:
        r = requests.post(helius_url, json=payload, timeout=10)
        if r.status_code == 200:
            res = r.json()
            if "result" in res:
                lamports = res["result"]["value"]
                sol_balance = lamports / 1_000_000_000
                print(f"WALLET_ADDRESS: {wallet_address}")
                print(f"BALANCE_SOL: {sol_balance:.6f}")
            else:
                print(f"RPC_ERROR: {res.get('error')}")
        else:
            print(f"HTTP_ERROR: Code {r.status_code}")
    except Exception as e:
        print(f"CONNECTION_ERROR: {str(e)}")

if __name__ == "__main__":
    check_live_balance()
