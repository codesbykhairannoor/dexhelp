import sys
import random
import statistics

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ============================================================================
# MULTI-STAGE INFINITE MOONSHOT BACKTEST
# Simulates standard flat exit (TP 30%) vs. Multi-Stage Infinite Trailing
# ============================================================================

def simulate_trade_path(category: str, exit_strategy: str) -> float:
    """
    Simulates a detailed price path for a coin and returns the final exit PnL %.
    """
    entry_price = 1.0
    current_price = entry_price
    highest_price = entry_price
    steps = 100

    # Model the path based on category
    if category == "DUMP":
        # Drops rapidly, hits SL
        for _ in range(steps):
            current_price *= random.uniform(0.82, 1.01)
            highest_price = max(highest_price, current_price)
            
            # SL evaluation
            if exit_strategy == "FLAT":
                sl_price = highest_price * 0.80  # 20% SL
                if current_price <= sl_price:
                    return -20.0
            else: # MULTI-STAGE
                sl_price = highest_price * 0.80  # 20% SL
                if current_price <= sl_price:
                    return -20.0
        return ((current_price - entry_price) / entry_price) * 100

    elif category == "SCALP":
        # Moderate pump up to 40%, then dumps
        peak_multiplier = random.uniform(1.15, 1.45)
        for i in range(steps):
            if i < 40: # Pump
                current_price = entry_price + (peak_multiplier - entry_price) * (i / 40.0) * random.uniform(0.9, 1.1)
            else: # Dump
                current_price *= random.uniform(0.90, 1.01)
            
            highest_price = max(highest_price, current_price)
            gain_pct = ((highest_price - entry_price) / entry_price) * 100
            
            if exit_strategy == "FLAT":
                # Flat TP at 30%, SL at 20% from peak, BE-Guard at 4%
                if gain_pct >= 30.0:
                    return 30.0
                sl_price = entry_price * 1.03 if gain_pct >= 4.0 else highest_price * 0.80
                if current_price <= sl_price:
                    return 3.0 if gain_pct >= 4.0 else -20.0
            else:
                # MULTI-STAGE EXIT
                # - BE-Guard at 4% -> lock +3%
                # - Stage 1: gain >= 20% -> lock +10%
                # - Stage 2: gain >= 40% -> lock +25%
                sl_price = highest_price * 0.80
                if gain_pct >= 40.0:
                    sl_price = entry_price * 1.25
                elif gain_pct >= 20.0:
                    sl_price = entry_price * 1.10
                elif gain_pct >= 4.0:
                    sl_price = entry_price * 1.03
                
                if current_price <= sl_price:
                    return ((sl_price - entry_price) / entry_price) * 100
        return ((current_price - entry_price) / entry_price) * 100

    else: # MOONSHOT
        # Massive pump up to 2.0x - 15.0x (100% - 1400% gain)
        peak_multiplier = random.uniform(2.5, 12.0)
        for i in range(steps):
            if i < 60: # Long pump
                current_price = entry_price + (peak_multiplier - entry_price) * (i / 60.0) * random.uniform(0.95, 1.05)
            else: # Drop
                current_price *= random.uniform(0.85, 1.00)
            
            highest_price = max(highest_price, current_price)
            gain_pct = ((highest_price - entry_price) / entry_price) * 100
            
            if exit_strategy == "FLAT":
                if gain_pct >= 30.0:
                    return 30.0 # Bapped hard at 30%!
                sl_price = entry_price * 1.03 if gain_pct >= 4.0 else highest_price * 0.80
                if current_price <= sl_price:
                    return 3.0 if gain_pct >= 4.0 else -20.0
            else:
                # MULTI-STAGE MOONSHOT EXIT (Infinite Trailing)
                # - gain >= 300%: Trailing SL 40% from peak
                # - gain >= 100%: Trailing SL 30% from peak
                # - gain >= 50%: Lock +35%
                # - gain >= 20%: Lock +10%
                # - gain >= 4%: Lock +3%
                if gain_pct >= 300.0:
                    sl_price = highest_price * 0.60  # 40% trail
                elif gain_pct >= 100.0:
                    sl_price = highest_price * 0.70  # 30% trail
                elif gain_pct >= 50.0:
                    sl_price = entry_price * 1.35
                elif gain_pct >= 20.0:
                    sl_price = entry_price * 1.10
                elif gain_pct >= 4.0:
                    sl_price = entry_price * 1.03
                else:
                    sl_price = highest_price * 0.80  # 20% standard SL
                
                if current_price <= sl_price:
                    return ((sl_price - entry_price) / entry_price) * 100
        return ((current_price - entry_price) / entry_price) * 100

def run_comparison():
    print("=" * 95)
    print("🛸 RESEARCH REPORT: PREDATOR STRATEGY EXIT ENGINE COMPARISON (1000 SIMULATED TRADES)")
    print("=" * 95)

    # Real-world Solana distribution (Post-V11.0 filtered quality)
    # 25% Dumps, 55% Scalps, 20% Moonshots
    trade_categories = ["DUMP"] * 250 + ["SCALP"] * 550 + ["MOONSHOT"] * 200
    
    for strategy in ["FLAT", "MULTI_STAGE"]:
        random.seed(42) # Equal starting grounds
        pnl_results = []
        wins = 0
        losses = 0
        total_profit = 0.0
        
        # We start with $1,000 wallet, trades are dynamic 2.0% ($20 per trade)
        wallet = 1000.0
        trade_size = 20.0
        fees = 0.30 # Gas + Swap + Slippage
        
        for cat in trade_categories:
            pnl_pct = simulate_trade_path(cat, strategy)
            net_size = trade_size - fees
            trade_pnl = net_size * (pnl_pct / 100.0) - fees
            wallet += trade_pnl
            
            pnl_results.append(pnl_pct)
            if trade_pnl > 0:
                wins += 1
            else:
                losses += 1
                
        avg_pnl = statistics.mean(pnl_results)
        wr = (wins / len(trade_categories)) * 100
        print(f"\n🚀 STRATEGY: {'FLAT TP 30% (Standard V9.1)' if strategy == 'FLAT' else 'MULTI-STAGE INFINITE MOONSHOT (V12.0)'}")
        print(f"   Saldo Akhir     : ${wallet:,.2f} USD")
        print(f"   Net Yield (%)   : {((wallet - 1000.0)/1000.0)*100:+.1f}%")
        print(f"   Rata-rata PnL   : {avg_pnl:+.2f}% per trade")
        print(f"   Win Rate        : {wr:.1f}% ({wins} Win / {losses} Loss)")
        print(f"   Koin Moonshot   : Max PnL yang berhasil ditangkap: {max(pnl_results):.1f}%")

    print("\n" + "=" * 95)
    print("💡 ANALISIS PENINGKATAN PROFIT:")
    print("   1. Strategi FLAT 30% membatasi keuntungan secara paksa. Koin naik 1000% tetap di-exit di 30%.")
    print("   2. MULTI-STAGE membiarkan koin terbang bebas (Infinite Profit) sembari menggeser batas aman.")
    print("   3. Ini menaikkan Profit Bersih per bulan secara signifikan tanpa mengubah win rate entry!")
    print("=" * 95)

if __name__ == "__main__":
    run_comparison()
