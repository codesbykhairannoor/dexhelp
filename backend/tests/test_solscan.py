import os
import sys
import requests
import json

# Fix Windows terminal encoding
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def test_solscan():
    print("=" * 80)
    print("SOLSCAN PRO API V2.0 DIAGNOSTIC TEST")
    print("=" * 80)
    
    # Try to load from .env
    token = os.getenv("SOLSCAN_API_KEY")
    if not token:
        # Fallback to look at parent directory .env (3 levels up from tests folder)
        parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        env_path = os.path.join(parent_dir, ".env")
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    if "SOLSCAN_API_KEY" in line and "=" in line:
                        token = line.split("=")[-1].strip().strip('"').strip("'")
                        break
                        
    if not token:
        print("[ERROR] SOLSCAN_API_KEY tidak ditemukan di .env file!")
        return
        
    print(f"Token Found (Length: {len(token)})")
    
    # Standard USDC token for test
    TEST_TOKEN = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    url = f"https://pro-api.solscan.io/v2.0/token/meta?address={TEST_TOKEN}"
    headers = {
        "token": token,
        "Accept": "application/json"
    }
    
    print(f"\nSending GET request to: {url}")
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"HTTP Status Code: {r.status_code}")
        
        if r.status_code == 200:
            print("[SUCCESS] API Key valid dan memiliki akses Pro Plan!")
            print("Response Data:")
            print(json.dumps(r.json(), indent=2))
        elif r.status_code == 401:
            res_body = r.json()
            err = res_body.get("error_message", "")
            print("[INFO] API Key valid, namun merupakan PLAN FREE (Starter).")
            print(f"Detail Error: {err}")
            print("\n💡 APAKAH BOT AKAN ERROR?")
            print("   TIDAK! Bot Predator V13.0 sudah dilengkapi dengan 'Silent Fallback Security'.")
            print("   Jika token Anda plan Free, bot akan otomatis beralih menggunakan RugCheck & GoPlus.")
            print("   Jika suatu hari Anda upgrade plan Solscan ke Pro, bot otomatis langsung memakai Solscan.")
        else:
            print(f"[ERROR] Solscan API mengembalikan status: {r.status_code}")
            print(f"Response: {r.text}")
            
    except Exception as e:
        print(f"[EXCEPTION] Gagal melakukan request: {e}")

if __name__ == "__main__":
    test_solscan()
