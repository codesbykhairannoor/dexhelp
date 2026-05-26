import json
import os
from datetime import datetime

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PORTFOLIO_FILE = os.path.join(CURRENT_DIR, "paper_portfolio.json")

def format_price(price):
    if price is None:
        return "-"
    if price < 0.0001:
        return f"${price:.8f}"
    return f"${price:.4f}"

def view_portfolio():
    if not os.path.exists(PORTFOLIO_FILE):
        print("❌ File paper_portfolio.json tidak ditemukan!")
        return

    try:
        with open(PORTFOLIO_FILE, "r") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Gagal membaca file: {e}")
        return

    print("\n" + "="*85)
    print("📈 DEX PREDATOR - LAPORAN PAPER PORTFOLIO")
    print("="*85)
    print(f"💰 Modal Awal   : ${data.get('initial_capital', 1000):.2f}")
    print(f"💵 Saldo Saat Ini: ${data.get('wallet_balance', 0):.2f}")
    
    # Hitung PnL Sementara dari trade yang sudah close
    closed_pnl = data.get('wallet_balance', 1000) - data.get('initial_capital', 1000)
    print(f"📉 PnL Realized : ${closed_pnl:.2f}")
    print("="*85)

    active_pos = data.get("active_positions", {})
    if active_pos:
        print("\n🟢 POSISI AKTIF (BELUM TERJUAL):")
        print("-" * 85)
        print(f"{'SYMBOL':<10} | {'ENTRY PRICE':<13} | {'HIGHEST (PUNCAK)':<18} | {'INVESTMENT':<10} | {'WAKTU MASUK'}")
        print("-" * 85)
        for addr, pos in active_pos.items():
            sym = pos.get('symbol', 'UNKNOWN')
            entry = format_price(pos.get('entry_price'))
            highest = format_price(pos.get('highest_price'))
            inv = f"${pos.get('gross_investment', 0):.2f}"
            time = pos.get('entry_time', '-')
            print(f"{sym:<10} | {entry:<13} | {highest:<18} | {inv:<10} | {time}")
        print("-" * 85)
    else:
        print("\n🟢 POSISI AKTIF: Kosong")

    history = data.get("trade_history", [])
    if history:
        print("\n📕 RIWAYAT TRANSAKSI (TERJUAL):")
        print("-" * 115)
        print(f"{'SYMBOL':<10} | {'ENTRY':<13} | {'EXIT (SL/TP)':<13} | {'HIGHEST':<13} | {'PNL %':<8} | {'PNL USD':<8} | {'ALASAN / TRIGGER'}")
        print("-" * 115)
        # Tampilkan maksimal 20 transaksi terakhir
        for trade in history[-20:]:
            sym = trade.get('symbol', 'UNKNOWN')
            entry = format_price(trade.get('entry_price'))
            exit_p = format_price(trade.get('exit_price'))
            
            # Coba ambil highest_price_reached (kalau ada dari versi baru)
            highest = trade.get('highest_price_reached')
            highest_str = format_price(highest) if highest else "-"
            
            pnl_pct = trade.get('pnl_pct', 0)
            pnl_usd = trade.get('pnl_usd', 0)
            
            # Formatting warna ANSI (Hijau kalau profit, Merah kalau rugi)
            # Di terminal biasa kadang tidak muncul, tapi aman
            pnl_pct_str = f"{pnl_pct:+.2f}%"
            pnl_usd_str = f"${pnl_usd:+.2f}"
            
            reason = trade.get('exit_reason', 'UNKNOWN')
            
            print(f"{sym:<10} | {entry:<13} | {exit_p:<13} | {highest_str:<13} | {pnl_pct_str:<8} | {pnl_usd_str:<8} | {reason}")
        print("-" * 115)
        print(f"Total Riwayat: {len(history)} transaksi. (Hanya menampilkan 20 terakhir)")
    else:
        print("\n📕 RIWAYAT TRANSAKSI: Belum ada transaksi yang ditutup.")
    print("\n")

if __name__ == "__main__":
    view_portfolio()
