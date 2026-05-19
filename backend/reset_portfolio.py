import os
import json
import sys

# Fix Windows terminal encoding for Emojis
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def reset_portfolio():
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    PORTFOLIO_FILE = os.path.join(CURRENT_DIR, "paper_portfolio.json")
    
    clean_state = {
        "wallet_balance": 1000.0,
        "initial_capital": 1000.0,
        "active_positions": {},
        "trade_history": [],
        "cooldowns": {}
    }
    
    try:
        with open(PORTFOLIO_FILE, "w") as f:
            json.dump(clean_state, f, indent=4)
        print("=" * 80)
        print("🗑️  DATABASE PORTFOLIO BERHASIL DIRESET!")
        print("   Semua riwayat transaksi lama dihapus.")
        print("   Modal dikembalikan murni ke $1,000.00 USD.")
        print("=" * 80)
    except Exception as e:
        print(f"[ERROR] Gagal mereset database: {e}")

if __name__ == "__main__":
    reset_portfolio()
