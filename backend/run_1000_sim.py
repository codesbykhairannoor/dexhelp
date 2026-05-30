import sys
import time
import random
import statistics

# Fix Windows terminal encoding for Emojis
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def run_1000_trades_simulation(initial_capital: float = 100.0, trade_allocation_pct: float = 0.10):
    """
    Simulasi 1000 Trade - Dex Screener Bot
    Mensimulasikan bagaimana bot akan berjalan selama kurang lebih 200 hari
    (dengan asumsi rata-rata 5 trade per hari).
    """
    random.seed(42) # For reproducible results
    
    total_trades_to_simulate = 1000
    avg_trades_per_day = 5
    estimated_days = total_trades_to_simulate // avg_trades_per_day
    
    print("=" * 80)
    print(f"🚀 PREDATOR GEMS - SIMULASI EKSKLUSIF {total_trades_to_simulate} TRADES")
    print(f"💰 Modal Awal       : ${initial_capital:.2f}")
    print(f"💼 Alokasi per Trade: {trade_allocation_pct * 100:.0f}% dari Saldo Saat Ini")
    print(f"📅 Estimasi Waktu   : {estimated_days} Hari (Asumsi {avg_trades_per_day} trade/hari)")
    print("=" * 80)
    
    current_wallet = initial_capital
    trailing_sl_pct = 0.20 # 20% SL default
    
    # Fees
    gas_fee = 0.05 # Realistic Solana gas fee (priority)
    swap_fee_pct = 0.005 # 0.5% Jupiter fee
    slippage_pct = 0.01 # 1% slippage
    
    wins = 0
    losses = 0
    
    wallet_history = [initial_capital]
    daily_trade_counts = []
    
    trade_counter = 0
    day = 1
    
    print("[SYSTEM] Memulai simulasi 1000 trade berdasarkan kondisi market real...", flush=True)
    time.sleep(1)
    
    while trade_counter < total_trades_to_simulate:
        if current_wallet < 5.0:
            print(f"❌ [MARGIN CALL] Saldo habis di trade ke-{trade_counter} (${current_wallet:.2f}). Simulasi dihentikan.")
            break
            
        # Simulasikan jumlah trade hari ini (antara 3 sampai 8 trade, mirip dex_hunter)
        trades_today = random.randint(3, 8)
        daily_trade_counts.append(trades_today)
        
        for _ in range(trades_today):
            if trade_counter >= total_trades_to_simulate:
                break
                
            trade_counter += 1
            trade_allocation = current_wallet * trade_allocation_pct
            
            # Biaya trade
            cost_per_trade = gas_fee + (trade_allocation * swap_fee_pct) + (trade_allocation * slippage_pct)
            net_entry = trade_allocation - cost_per_trade
            
            # Simulasi harga (DUMP, SCALP, MOONSHOT)
            category = random.choices(["DUMP", "SCALP", "MOONSHOT"], weights=[0.10, 0.60, 0.30])[0]
            
            entry_price = 1.0
            highest_price = entry_price
            current_price = entry_price
            steps = 40
            exit_price = entry_price
            
            take_profit_pct = 0.20 # 20% TP
            trailing_sl_pct = 0.08 # 8% SL
            
            if category == "DUMP":
                # Kena Initial SL atau Rugpull
                for _ in range(steps):
                    current_price *= random.uniform(0.85, 1.01)
                    highest_price = max(highest_price, current_price)
                    sl_price = highest_price * (1 - trailing_sl_pct)
                    if current_price >= entry_price * (1 + take_profit_pct):
                        exit_price = current_price
                        break
                    if current_price <= sl_price:
                        exit_price = sl_price
                        break
                else:
                    exit_price = current_price
                    
            elif category == "SCALP":
                # Naik sedikit lalu retrace
                for step in range(steps):
                    if step < 15:
                        current_price *= random.uniform(0.97, 1.05)
                    else:
                        current_price *= random.uniform(0.92, 1.02)
                        
                    highest_price = max(highest_price, current_price)
                    sl_price = highest_price * (1 - trailing_sl_pct)
                    if current_price >= entry_price * (1 + take_profit_pct):
                        exit_price = current_price
                        break
                    if current_price <= sl_price:
                        exit_price = sl_price
                        break
                else:
                    exit_price = current_price
                    
            else:
                # MOONSHOT (Naik kencang)
                for step in range(steps):
                    if step < 25:
                        current_price *= random.uniform(0.99, 1.15)
                    else:
                        current_price *= random.uniform(0.88, 1.02)
                        
                    highest_price = max(highest_price, current_price)
                    
                    # Trailing SL dinamis untuk Moonshot
                    if highest_price >= 2.0: # Profit 100%
                        sl_price = highest_price * 0.70 # TSL 30%
                    else:
                        sl_price = highest_price * (1 - trailing_sl_pct)
                        
                    # Let moonshots ride a bit longer, TP at 40%
                    if current_price >= entry_price * (1 + take_profit_pct * 2):
                        exit_price = current_price
                        break
                    if current_price <= sl_price:
                        exit_price = sl_price
                        break
                else:
                    exit_price = current_price
            
            trade_yield_pct = ((exit_price - entry_price) / entry_price) * 100
            trade_pnl = net_entry * (trade_yield_pct / 100)
            
            if trade_pnl > 0:
                wins += 1
            else:
                losses += 1
                
            current_wallet += trade_pnl
            wallet_history.append(current_wallet)
            
            if trade_counter % 100 == 0:
                print(f"  [TRADE #{trade_counter:04d}] Saldo Saat Ini: ${current_wallet:<10.2f} | Kategori Exit: {category}")
                
        day += 1

    print("-" * 80)
    print("🏆 HASIL SIMULASI 1000 TRADES (REALISTIC CONDITIONS)")
    print("-" * 80)
    
    win_rate = (wins / trade_counter) * 100 if trade_counter > 0 else 0
    net_pnl_usd = current_wallet - initial_capital
    net_pnl_pct = (net_pnl_usd / initial_capital) * 100
    
    # Drawdown
    max_peak = initial_capital
    max_dd = 0.0
    for w in wallet_history:
        if w > max_peak:
            max_peak = w
        dd = ((max_peak - w) / max_peak) * 100
        if dd > max_dd:
            max_dd = dd
            
    avg_trades_daily = sum(daily_trade_counts) / len(daily_trade_counts) if daily_trade_counts else 0

    print(f"  💰 Modal Awal              : ${initial_capital:.2f}")
    print(f"  💵 Saldo Akhir             : ${current_wallet:.2f}")
    print(f"  📈 Profit Bersih (USD)     : {net_pnl_usd:+.2f}")
    print(f"  📊 ROI / Keuntungan (%)    : {net_pnl_pct:+.2f}% (Efek Compounding)")
    print(f"  ✅ Win Rate Strategy       : {win_rate:.1f}% ({wins} Menang / {losses} Kalah)")
    print(f"  📉 Maksimum Drawdown (Resiko): {max_dd:.1f}%")
    print(f"  ⏱️ Rata-rata Trade Harian  : {avg_trades_daily:.1f} trade per hari (diambil dari {len(daily_trade_counts)} hari)")
    print("=" * 80)

if __name__ == "__main__":
    run_1000_trades_simulation()
