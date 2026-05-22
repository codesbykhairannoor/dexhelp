import json
import os

PORTFOLIO_FILE = os.path.join(os.path.dirname(__file__), "paper_portfolio.json")

def cek_riwayat():
    if not os.path.exists(PORTFOLIO_FILE):
        print("❌ Belum ada riwayat. Portofolio kosong atau belum ada koin yang dibeli.")
        return

    try:
        with open(PORTFOLIO_FILE, "r") as f:
            data = json.load(f)
            
        print("=" * 60)
        print("💰 LAPORAN KEUANGAN VIRTUAL (PAPER TRADER) 💰")
        print("=" * 60)
        
        balance = data.get("wallet_balance", 0.0)
        initial = data.get("initial_capital", 1000.0)
        net_pnl = balance - initial
        
        print(f"Modal Awal      : ${initial:,.2f}")
        print(f"Saldo Saat Ini  : ${balance:,.2f}")
        print(f"Total Keuntungan: {'+$' if net_pnl >= 0 else '-$'}{abs(net_pnl):,.2f}")
        print("-" * 60)
        
        active = data.get("active_positions", {})
        print(f"🟢 POSISI AKTIF (SEDANG DIBELI): {len(active)} Koin")
        for addr, pos in active.items():
            print(f"  -> {pos.get('symbol')} | Harga Masuk: ${pos.get('entry_price'):.6f} | Modal: ${pos.get('gross_investment'):.2f}")
            
        print("-" * 60)
        
        history = data.get("trade_history", [])
        print(f"📜 RIWAYAT PENJUALAN (SELESAI): {len(history)} Transaksi")
        if not history:
            print("   (Belum ada koin yang dijual. Mesin sedang menunggu mangsa!)")
        else:
            # Tampilkan 10 riwayat terakhir saja agar terminal tidak penuh
            for t in history[-10:]:
                pnl_usd = t.get("pnl_usd", 0.0)
                pnl_pct = t.get("pnl_pct", 0.0)
                simbol = t.get("symbol", "UNKNOWN")
                print(f"  -> Jual {simbol} | Untung/Rugi: {'+$' if pnl_usd >= 0 else '-$'}{abs(pnl_usd):.2f} ({pnl_pct:+.2f}%)")
        
        print("=" * 60)

    except Exception as e:
        print(f"Terjadi kesalahan saat membaca file: {e}")

if __name__ == "__main__":
    cek_riwayat()
