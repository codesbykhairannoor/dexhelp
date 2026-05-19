import os
import sys
import json
import argparse

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PORTFOLIO_FILE = os.path.join(CURRENT_DIR, "paper_portfolio.json")

def load_portfolio() -> dict:
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "wallet_balance": 1000.00,
        "initial_capital": 1000.00,
        "active_positions": {},
        "trade_history": [],
        "cooldowns": {}
    }

def save_portfolio(portfolio: dict):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(portfolio, f, indent=4)

def main():
    parser = argparse.ArgumentParser(description="Solana Dex Predator - Paper Wallet Manager")
    parser.add_argument("--status", action="store_true", help="Lihat status dompet simulasi saat ini")
    parser.add_argument("--set-balance", type=float, help="Ubah saldo tunai saat ini tanpa menghapus riwayat/posisi")
    parser.add_argument("--set-initial", type=float, help="Ubah modal awal (Murni) untuk audit PnL")
    parser.add_argument("--wipe", action="store_true", help="RESET TOTAL: Hapus semua posisi, riwayat, dan cooldown")
    
    args = parser.parse_args()
    portfolio = load_portfolio()
    
    if args.wipe:
        confirm = input("⚠️ Apakah Anda yakin ingin melakukan RESET TOTAL? Semua riwayat trade & posisi aktif akan HAPUS! (y/N): ")
        if confirm.lower() == 'y':
            new_portfolio = {
                "wallet_balance": 1000.00,
                "initial_capital": 1000.00,
                "active_positions": {},
                "trade_history": [],
                "cooldowns": {}
            }
            save_portfolio(new_portfolio)
            print("🟢 Database portofolio telah di-reset total ke saldo awal $1000.00!")
        else:
            print("🔴 Reset dibatalkan.")
        return
        
    updated = False
    
    if args.set_balance is not None:
        portfolio["wallet_balance"] = args.set_balance
        updated = True
        print(f"🟢 Saldo tunai berhasil diubah menjadi: ${args.set_balance:.4f}")
        
    if args.set_initial is not None:
        portfolio["initial_capital"] = args.set_initial
        updated = True
        print(f"🟢 Modal awal (Murni) berhasil diubah menjadi: ${args.set_initial:.4f}")
        
    if updated:
        save_portfolio(portfolio)
        
    # Print current status
    print("=" * 60)
    print("🛰️  STATUS DATABASE SIMULASI PAPER TRADER")
    print("=" * 60)
    print(f"  Modal Awal (Murni) : ${portfolio.get('initial_capital', 1000.00):,.2f}")
    print(f"  Saldo Tunai Dompet : ${portfolio.get('wallet_balance', 1000.00):,.4f}")
    print(f"  Posisi Aktif       : {len(portfolio.get('active_positions', {}))} Koin")
    print(f"  Riwayat Closed     : {len(portfolio.get('trade_history', []))} Transaksi")
    print(f"  Koin Cooldown      : {len(portfolio.get('cooldowns', {}))} Koin")
    print("=" * 60)
    print("\n💡 Petunjuk Penggunaan:")
    print("  Ubah Saldo Tunai   : python backend/paper_wallet_manager.py --set-balance 500")
    print("  Ubah Modal Awal    : python backend/paper_wallet_manager.py --set-initial 1000")
    print("  Reset Total DB     : python backend/paper_wallet_manager.py --wipe")

if __name__ == "__main__":
    main()
