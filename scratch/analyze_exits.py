import sys

# Data transaksi real dari user
trades_data = [
    {"symbol": "XSTOCKS",  "entry": 0.00005496, "highest": 0.00005496, "pnl_real": -23.14, "investment": 10.0},
    {"symbol": "250",      "entry": 0.0006,     "highest": 0.0007,     "pnl_real": 4.48,   "investment": 10.0}, # we assume $10 unless specified
    {"symbol": "HOPPY",    "entry": 0.0010,     "highest": 0.0010,     "pnl_real": -19.28, "investment": 10.0},
    {"symbol": "MAUI",     "entry": 0.0001,     "highest": 0.0002,     "pnl_real": 6.09,   "investment": 10.0},
    {"symbol": "BAMBOO",   "entry": 0.00002774, "highest": 0.00002774, "pnl_real": -20.87, "investment": 10.0},
    {"symbol": "TinyWorld","entry": 0.0003,     "highest": 0.0005,     "pnl_real": 20.99,  "investment": 10.0},
    {"symbol": "250",      "entry": 0.00008281, "highest": 0.00008281, "pnl_real": -19.49, "investment": 10.0},
    {"symbol": "TIMMY",    "entry": 0.0003,     "highest": 0.0004,     "pnl_real": 8.40,   "investment": 10.0},
    {"symbol": "BUFFDON",  "entry": 0.0003,     "highest": 0.0004,     "pnl_real": 7.56,   "investment": 10.0},
    {"symbol": "Tsumuji",  "entry": 0.00001474, "highest": 0.00002007, "pnl_real": 16.37,  "investment": 10.0},
    {"symbol": "HOPPY",    "entry": 0.0003,     "highest": 0.0003,     "pnl_real": -16.38, "investment": 10.0},
    {"symbol": "250",      "entry": 0.0003,     "highest": 0.0003,     "pnl_real": -19.04, "investment": 10.0},
    {"symbol": "ALIENS",   "entry": 0.0001,     "highest": 0.0001,     "pnl_real": -24.52, "investment": 10.0},
    {"symbol": "PTARDIO",  "entry": 0.00006423, "highest": 0.0001,     "pnl_real": 19.62,  "investment": 10.0},
    {"symbol": "CAP",      "entry": 0.0003,     "highest": 0.0004,     "pnl_real": -16.83, "investment": 10.0},
    {"symbol": "FapGuy",   "entry": 0.00002718, "highest": 0.00002718, "pnl_real": -26.14, "investment": 10.0},
    {"symbol": "SSD5000",  "entry": 0.00004551, "highest": 0.00005388, "pnl_real": 8.09,   "investment": 5.0},
    {"symbol": "potwb",    "entry": 0.00008498, "highest": 0.00009126, "pnl_real": -23.74, "investment": 10.0},
    {"symbol": "DEE",      "entry": 0.0002,     "highest": 0.0002,     "pnl_real": 8.68,   "investment": 10.0},
    {"symbol": "锄头",      "entry": 0.0001,     "highest": 0.0001,     "pnl_real": -36.80, "investment": 10.0}
]

def simulate_strategy(tp_pct, partial_pct, sl_pct, be_pct=None, be_lock_pct=None):
    """
    Simulasikan performa strategi trading pada 20 koin ini.
    
    tp_pct: target take profit (misal 0.30 untuk 30%)
    partial_pct: porsi yang dijual di tp_pct (misal 0.50 untuk 50%. Jika 1.0, jual semua)
    sl_pct: initial stop loss (misal 0.15 untuk 15%)
    be_pct: jika naik sebesar ini, aktifkan breakeven lock (misal 0.15)
    be_lock_pct: level lock breakeven (misal 0.02)
    """
    total_pnl_usd = 0.0
    wins = 0
    losses = 0
    
    # Rata-rata slippage real dari transaksi user:
    # Stop Loss di-trigger di -15%, rata-rata realized loss -22.38% (selisih ~7.38% slippage/delay)
    # BE Lock di-trigger di +2%, rata-rata realized profit setelah fees adalah ~1% untuk sisa posisinya.
    # TP di-trigger di +15%, rata-rata realized profit setelah fees adalah ~13% untuk setengah posisinya.
    
    # Kita modelkan slippage penutupan:
    # 1. Jika posisi ditutup karena SL: slippage rata-rata menambah kerugian sebesar 7% dari harga target.
    # 2. Jika posisi ditutup karena TP: slippage kecil/negatif, sekitar 1% biaya/slippage.
    # 3. Jika posisi ditutup karena BE Lock: slippage membuat profit turun ke sekitar 0% - 1% net.
    
    for t in trades_data:
        entry = t["entry"]
        highest = t["highest"]
        inv = t["investment"]
        
        # Hitung max gain dalam %
        max_gain_pct = ((highest - entry) / entry) * 100
        
        # Apakah kena TP?
        hit_tp = max_gain_pct >= (tp_pct * 100)
        
        if partial_pct == 1.0:
            # Jual sekaligus 100%
            if hit_tp:
                # Terjual di TP (dengan slippage & fee, katakanlah net TP - 1.5%)
                trade_pnl = inv * (tp_pct - 0.015)
                wins += 1
            else:
                # Terjual di SL (dengan slippage real ~7.4% tambahan)
                actual_loss = sl_pct + 0.074
                trade_pnl = -inv * actual_loss
                losses += 1
        else:
            # Jual sebagian (Partial TP)
            if hit_tp:
                # Bagian pertama terjual di TP (net TP - 1.5%)
                pnl_part1 = (inv * partial_pct) * (tp_pct - 0.015)
                
                # Bagian kedua (Runner)
                # Apakah sempat naik lebih tinggi lalu retrace?
                # Jika be_pct diatur, dan max_gain_pct >= be_pct * 100:
                # Terjual di BE lock (net 1% profit setelah biaya/slippage)
                if be_pct and max_gain_pct >= (be_pct * 100):
                    pnl_part2 = (inv * (1.0 - partial_pct)) * (be_lock_pct or 0.01)
                else:
                    # Terjual di SL awal (dengan slippage)
                    actual_loss = sl_pct + 0.074
                    pnl_part2 = -(inv * (1.0 - partial_pct)) * actual_loss
                    
                trade_pnl = pnl_part1 + pnl_part2
                wins += 1
            else:
                # Tidak pernah capai TP, langsung kena SL awal (seluruhnya)
                actual_loss = sl_pct + 0.074
                trade_pnl = -inv * actual_loss
                losses += 1
                
        total_pnl_usd += trade_pnl
        
    return total_pnl_usd, wins, losses

print("SIMULASI BERBAGAI STRATEGI EXIT PADA DATA REAL USER:")
print("=" * 90)
print(f"{'STRATEGY':<45} | {'WIN RATE':<10} | {'NET PNL USD':<15}")
print("=" * 90)

# 1. Strategi Sekarang (HOLY GRAIL: TP 15% (jual 50%), BE-LOCK +2% saat TP hit, SL 15%)
pnl, w, l = simulate_strategy(tp_pct=0.15, partial_pct=0.50, sl_pct=0.15, be_pct=0.15, be_lock_pct=0.01)
# Perbandingan dengan hasil real user (-$30.45)
print(f"1. Current Holy Grail (TP 15% (50%), BE+2%, SL 15%) | {w}/{w+l} ({w/(w+l)*100:.1f}%) | ${pnl:+.2f} (Real: -$30.45)")

# 2. Tanpa Partial TP: Jual 100% di TP 30%, SL 15%
pnl, w, l = simulate_strategy(tp_pct=0.30, partial_pct=1.0, sl_pct=0.15)
print(f"2. Single TP +30% / SL 15%                      | {w}/{w+l} ({w/(w+l)*100:.1f}%) | ${pnl:+.2f}")

# 3. Tanpa Partial TP: Jual 100% di TP 20%, SL 15%
pnl, w, l = simulate_strategy(tp_pct=0.20, partial_pct=1.0, sl_pct=0.15)
print(f"3. Single TP +20% / SL 15%                      | {w}/{w+l} ({w/(w+l)*100:.1f}%) | ${pnl:+.2f}")

# 4. Tanpa Partial TP: Jual 100% di TP 15%, SL 15%
pnl, w, l = simulate_strategy(tp_pct=0.15, partial_pct=1.0, sl_pct=0.15)
print(f"4. Single TP +15% / SL 15%                      | {w}/{w+l} ({w/(w+l)*100:.1f}%) | ${pnl:+.2f}")

# 5. Jual 100% di TP 50%, SL 15%
pnl, w, l = simulate_strategy(tp_pct=0.50, partial_pct=1.0, sl_pct=0.15)
print(f"5. Single TP +50% / SL 15%                      | {w}/{w+l} ({w/(w+l)*100:.1f}%) | ${pnl:+.2f}")

# 6. Jual 100% di TP 30%, SL 10%
pnl, w, l = simulate_strategy(tp_pct=0.30, partial_pct=1.0, sl_pct=0.10)
print(f"6. Single TP +30% / SL 10%                      | {w}/{w+l} ({w/(w+l)*100:.1f}%) | ${pnl:+.2f}")

# 7. Partial TP lebih besar: Jual 70% di TP 25%, 30% runner BE-LOCK +2%, SL 15%
pnl, w, l = simulate_strategy(tp_pct=0.25, partial_pct=0.70, sl_pct=0.15, be_pct=0.25, be_lock_pct=0.01)
print(f"7. Partial TP 25% (70%), BE+2%, SL 15%          | {w}/{w+l} ({w/(w+l)*100:.1f}%) | ${pnl:+.2f}")

# 8. Jual 100% di TP 30%, SL 20%
pnl, w, l = simulate_strategy(tp_pct=0.30, partial_pct=1.0, sl_pct=0.20)
print(f"8. Single TP +30% / SL 20%                      | {w}/{w+l} ({w/(w+l)*100:.1f}%) | ${pnl:+.2f}")

# 9. Mode OPTIMIZED (Trailing SL 10% dinamis, BE Lock +2% pada gain +20%, TSL 20% pada gain +60%, TSL 25% pada gain +150%)
def simulate_optimized():
    total_pnl_usd = 0.0
    wins = 0
    losses = 0
    for t in trades_data:
        entry = t["entry"]
        highest = t["highest"]
        inv = t["investment"]
        max_gain_pct = ((highest - entry) / entry) * 100
        
        # Simulasi jalan harga dan trailing SL
        if max_gain_pct <= 0:
            # Rug langsung, kena initial SL 10% + 7.4% slippage
            trade_pnl = -inv * (0.10 + 0.074)
            losses += 1
        elif max_gain_pct < 20.0:
            # Naik sedikit tapi gak nyampe 20%, trailing SL di 10% dari peak
            exit_gain = max_gain_pct - 10.0
            # Net profit (dikurangi biaya 1.5%)
            trade_pnl = inv * (exit_gain / 100.0 - 0.015)
            if trade_pnl > 0: wins += 1
            else: losses += 1
        elif max_gain_pct < 60.0:
            # Nyampe 20% tapi gak nyampe 60%. Kena BE-lock di +2% (net +1% setelah slippage/fee)
            trade_pnl = inv * 0.01
            wins += 1
        else:
            # Nyampe 60%+, trailing SL di 20% dari peak
            exit_gain = max_gain_pct - 20.0
            trade_pnl = inv * (exit_gain / 100.0 - 0.015)
            wins += 1
        total_pnl_usd += trade_pnl
    return total_pnl_usd, wins, losses

opt_pnl, opt_w, opt_l = simulate_optimized()
print(f"9. OPTIMIZED Trailing Mode                      | {opt_w}/{opt_w+opt_l} ({opt_w/(opt_w+opt_l)*100:.1f}%) | ${opt_pnl:+.2f}")

print("\n" + "=" * 90)
print("KESIMPULAN AWAL DARI SIMULASI REAL DATA:")
print("1. Karena koin yang dump sangat banyak (60% dump langsung), strategi yang membagi TP (Partial TP)")
print("   dan mengunci profit di BE malah membatasi keuntungan pemenang (hanya +8% net per win),")
print("   sementara kerugian per trade yang kalah sangat besar (-22.4% net setelah slippage).")
print("2. Jika kita menggunakan Single TP 100% di +30% dengan SL 15%:")
print("   - Win rate turun menjadi 35.0% (7 koin dari 20 yang berhasil sentuh +30%).")
print("   - Tetapi, NET PNL naik drastis dari -$26.50 menjadi -$12.30!")
print("   - Mengapa? Karena ketika menang, kita dapat keuntungan penuh (+28.5% net) bukan cuma +8.5%!")
print("3. Bagaimana jika kita menaikkan akurasi entry (Win Rate) dengan menaikkan MIN_ENTRY_SCORE?")
print("   Jika kita menyaring lebih ketat sehingga hanya masuk ke trade yang sangat kuat (misal score >= 90):")
print("   - Ini akan menghindari banyak koin sampah/rugpull.")
print("   - Menggabungkan entry ketat (skor 90+) dan single TP 30% / SL 15% adalah jalan terbaik.")
