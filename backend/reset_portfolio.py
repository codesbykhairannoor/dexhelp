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
    
    target = "paper"
    if len(sys.argv) > 1:
        target = sys.argv[1].lower()
        
    clean_state = {
        "wallet_address": "",
        "wallet_balance": 1000.0,
        "initial_capital": 1000.0,
        "active_positions": {},
        "trade_history": [],
        "cooldowns": {}
    }
    
    targets = []
    if target == "paper" or target == "all":
        targets.append(("paper_portfolio.json", "PAPER PORTFOLIO (SIMULATOR)"))
    if target == "live" or target == "all":
        targets.append(("live_portfolio.json", "LIVE PORTFOLIO (REAL MONEY)"))
        
    if not targets:
        print(f"[ERROR] Target reset tidak dikenal: '{target}'. Gunakan: 'paper', 'live', atau 'all'")
        return
        
    print("=" * 80)
    for filename, label in targets:
        filepath = os.path.join(CURRENT_DIR, filename)
        
        # Reset balance for live portfolio dynamically from onchain wallet if exists
        state_to_write = clean_state.copy()
        if filename == "live_portfolio.json":
            # For live portfolio, balance will be dynamically updated by trading engine
            state_to_write["wallet_balance"] = 0.0
            state_to_write["initial_capital"] = 0.0
            
        try:
            with open(filepath, "w") as f:
                json.dump(state_to_write, f, indent=4)
            print(f"🗑️  DATABASE {label} BERHASIL DIRESET!")
            print(f"   Semua riwayat transaksi lama pada {filename} telah dihapus.")
        except Exception as e:
            print(f"[ERROR] Gagal mereset {label}: {e}")
            
    # Clear trades table in sqlite database
    try:
        db_path = os.path.join(CURRENT_DIR, "trading_bot.db")
        if os.path.exists(db_path):
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM trades")
            conn.commit()
            conn.close()
            print("🗑️  DATABASE SQL SQLite (trading_bot.db) trades table successfully cleared!")
    except Exception as e:
        print(f"[ERROR] Gagal mereset database SQL SQLite: {e}")
        
    print("=" * 80)

if __name__ == "__main__":
    reset_portfolio()
