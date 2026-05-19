import os
import sys
import json
import time
import requests

# Fix Windows terminal encoding for Emojis
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def run_evaluation_dashboard():
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    PORTFOLIO_FILE = os.path.join(CURRENT_DIR, "paper_portfolio.json")
    
    if not os.path.exists(PORTFOLIO_FILE):
        print("[ERROR] File paper_portfolio.json tidak ditemukan! Jalankan bot atau reset database terlebih dahulu.")
        return
        
    try:
        with open(PORTFOLIO_FILE, "r") as f:
            portfolio = json.load(f)
    except Exception as e:
        print(f"[ERROR] Gagal membaca file database: {e}")
        return
        
    wallet_balance = portfolio.get("wallet_balance", 1000.00)
    active_positions = portfolio.get("active_positions", {})
    trade_history = portfolio.get("trade_history", [])
    cooldowns = portfolio.get("cooldowns", {})
    initial_capital = portfolio.get("initial_capital", 1000.00)
    
    # Load JUPITER_API_KEY from .env
    jupiter_key = os.getenv("JUPITER_API_KEY", "jup_0872d0ca9886efca00560439b283c2bc25821ab36727457792ce61ca352c2f60")
    if not os.getenv("JUPITER_API_KEY"):
        parent_dir = os.path.dirname(CURRENT_DIR)
        env_path = os.path.join(parent_dir, ".env")
        if os.path.exists(env_path):
            with open(env_path, "r") as ef:
                for line in ef:
                    if "JUPITER_API_KEY" in line and "=" in line:
                        jupiter_key = line.split("=")[-1].strip().strip('"').strip("'")
                        break
                        
    # Fetch live prices for active positions
    price_map = {}
    if active_positions:
        addr_list = list(active_positions.keys())
        addr_str = ",".join(addr_list)
        url = f"https://api.jup.ag/price/v3?ids={addr_str}"
        headers = {"x-api-key": jupiter_key, "Accept": "application/json"}
        try:
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                res = r.json()
                for addr in addr_list:
                    tinfo = res.get(addr, {})
                    price = tinfo.get("usdPrice")
                    if price is not None:
                        price_map[addr] = float(price)
        except Exception:
            pass

    # --- CALCULATIONS ---
    total_active_value = 0.0
    active_positions_list = []
    
    for addr, pos in active_positions.items():
        entry_price = pos["entry_price"]
        net_investment = pos["net_investment"]
        qty = pos["qty"]
        current_price = price_map.get(addr, entry_price)
        current_val = qty * current_price
        pnl_usd = current_val - pos.get("gross_investment", net_investment)
        pnl_pct = ((current_price - entry_price) / entry_price) * 100
        
        total_active_value += current_val
        active_positions_list.append({
            "symbol": pos["symbol"],
            "entry_price": entry_price,
            "current_price": current_price,
            "invested": pos.get("gross_investment", net_investment),
            "current_val": current_val,
            "pnl_usd": pnl_usd,
            "pnl_pct": pnl_pct
        })
        
    total_portfolio_value = wallet_balance + total_active_value
    net_pnl_usd = total_portfolio_value - initial_capital
    net_pnl_pct = (net_pnl_usd / initial_capital) * 100 if initial_capital > 0 else 0.0
    
    # Win rate analytics
    wins = [t for t in trade_history if t.get("pnl_usd", 0) >= 0]
    losses = [t for t in trade_history if t.get("pnl_usd", 0) < 0]
    total_closed_trades = len(trade_history)
    win_rate = (len(wins) / total_closed_trades * 100) if total_closed_trades > 0 else 0.0
    
    avg_win = sum(t.get("pnl_usd", 0) for t in wins) / len(wins) if wins else 0.0
    avg_loss = sum(t.get("pnl_usd", 0) for t in losses) / len(losses) if losses else 0.0
    
    # Render dashboard
    print("=" * 80)
    print("🛰️  SOLANA DEX PREDATOR - LIVE PERFORMANCE EVALUATION DASHBOARD V9.1")
    print("=" * 80)
    
    # Section 1: Wallet Performance Summary
    print("[1] RINGKASAN PORTOFOLIO:")
    print(f"    Modal Awal (Murni) : ${initial_capital:,.2f} USD")
    print(f"    Saldo Kas Tunai     : ${wallet_balance:,.4f} USD")
    print(f"    Nilai Aset Aktif    : ${total_active_value:,.4f} USD")
    print(f"    TOTAL NILAI PORTO   : ${total_portfolio_value:,.4f} USD")
    print(f"    Akumulasi PnL Neto  : {net_pnl_pct:+.2f}% ({net_pnl_usd:+.2f} USD)")
    print("-" * 80)
    
    # Section 2: Active Positions Table
    print(f"[2] POSISI AKTIF YANG SEDANG DIPANTAU ({len(active_positions_list)}/10):")
    if active_positions_list:
        print(f"    {'SYMBOL':<10} | {'INVESTED':<10} | {'ENTRY PRICE':<12} | {'LIVE PRICE':<12} | {'PnL %':<10} | {'PnL USD'}")
        print("    " + "-" * 72)
        for pos in active_positions_list:
            print(f"    {pos['symbol']:<10} | ${pos['invested']:<9.2f} | ${pos['entry_price']:<11.8f} | ${pos['current_price']:<11.8f} | {pos['pnl_pct']:+.2f}% | {pos['pnl_usd']:+.2f} USD")
    else:
        print("    (Tidak ada posisi aktif saat ini)")
    print("-" * 80)
    
    # Section 3: Closed Trades History Table
    print(f"[3] RIWAYAT TRANSAKSI CLOSED ({total_closed_trades} Trades):")
    if trade_history:
        print(f"    {'SYMBOL':<10} | {'ENTRY PRICE':<12} | {'EXIT PRICE':<12} | {'PnL %':<10} | {'PnL USD':<10} | {'CLOSED TIME'}")
        print("    " + "-" * 72)
        # Show last 10 trades for cleaner view
        for t in trade_history[-10:]:
            print(f"    {t['symbol']:<10} | ${t['entry_price']:<11.8f} | ${t['exit_price']:<11.8f} | {t['pnl_pct']:+.2f}% | {t['pnl_usd']:+.2f} USD | {t['closed_at']}")
        if len(trade_history) > 10:
            print(f"    ... dan {len(trade_history) - 10} transaksi lama lainnya.")
    else:
        print("    (Belum ada transaksi selesai)")
    print("-" * 80)
    
    # Section 4: Quant Win/Loss Analytics
    print("[4] ANALISIS STATISTIK PRESTASI TRADING:")
    print(f"    Tingkat Kemenangan (Win Rate) : {win_rate:.1f}% ({len(wins)} Menang / {len(losses)} Kalah)")
    print(f"    Rata-rata Profit (Per Win)    : {avg_win:+.2f} USD")
    print(f"    Rata-rata Kerugian (Per Loss) : {avg_loss:+.2f} USD")
    print("-" * 80)
    
    # Section 5: Cooldown Shield Tracker
    print("[5] DAFTAR SHIELD COOLDOWN YANG AKTIF:")
    active_cooldowns = []
    current_time = time.time()
    for addr, end_time in cooldowns.items():
        time_left = int(end_time - current_time)
        if time_left > 0:
            # Try to match symbol from history or active, fallback to address
            sym = "UNKNOWN"
            for t in trade_history:
                if t["address"] == addr:
                    sym = t["symbol"]
                    break
            active_cooldowns.append(f"{sym} ({time_left // 3600}j {(time_left % 3600) // 60}m {(time_left % 60)}s)")
            
    if active_cooldowns:
        print("    " + ", ".join(active_cooldowns))
    else:
        print("    (Semua koin bersih dari cooldown, scanner bebas menyisir!)")
    print("=" * 80)

if __name__ == "__main__":
    run_evaluation_dashboard()
