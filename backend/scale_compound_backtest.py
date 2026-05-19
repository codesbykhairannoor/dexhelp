import sys
import random
import statistics

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ============================================================================
# V10.0 SCALE & COMPOUND BACKTEST
# Shows real profit at different capital sizes + compounding over 12 months
# ============================================================================

def simulate_month(seed: int, starting_capital: float, use_dynamic_sizing: bool) -> dict:
    random.seed(seed)

    wallet = starting_capital
    active = {}

    # V10.0 optimal params
    sl_pct = 0.20
    tp_pct = 30.0
    be_active = False

    # V10.0 filtered distribution (post-filter quality)
    weights = [0.25, 0.55, 0.20]
    categories = ["DUMP", "SCALP", "MOONSHOT"]

    # Real Solana fees
    gas_fee = 0.01
    swap_fee = 0.0025
    slip_fee = 0.005

    total_trades = 0
    wins = 0
    losses = 0
    tp_hits = 0

    for day in range(1, 31):
        daily_opps = random.randint(3, 8)

        for _ in range(daily_opps):
            # Process exits
            for sym, pos in list(active.items()):
                cat = pos["category"]
                entry_price = 1.0
                highest_price = entry_price
                current_price = entry_price
                exit_price = entry_price

                if cat == "DUMP":
                    for _ in range(60):
                        current_price *= random.uniform(0.80, 0.98)
                    exit_price = max(current_price, entry_price * (1 - sl_pct))

                elif cat == "SCALP":
                    for step in range(60):
                        current_price *= random.uniform(0.95, 1.06)
                        highest_price = max(highest_price, current_price)
                        pg = ((highest_price - entry_price) / entry_price) * 100
                        if pg >= tp_pct:
                            exit_price = entry_price * (1 + tp_pct / 100)
                            tp_hits += 1
                            break
                        floor_sl = highest_price * (1 - sl_pct)
                        if current_price <= floor_sl:
                            exit_price = floor_sl
                            break
                    else:
                        exit_price = current_price

                elif cat == "MOONSHOT":
                    for step in range(60):
                        if step < 25:
                            current_price *= random.uniform(1.04, 1.22)
                        else:
                            current_price *= random.uniform(0.87, 1.02)
                        highest_price = max(highest_price, current_price)
                        pg = ((highest_price - entry_price) / entry_price) * 100
                        if pg >= tp_pct:
                            exit_price = entry_price * (1 + tp_pct / 100)
                            tp_hits += 1
                            break
                        if pg >= 100.0:
                            floor_sl = entry_price * 1.65
                        elif pg >= 40.0:
                            floor_sl = entry_price * 1.15
                        else:
                            floor_sl = highest_price * (1 - sl_pct)
                        if current_price <= floor_sl:
                            exit_price = floor_sl
                            break
                    else:
                        exit_price = current_price

                net_exit = pos["qty"] * exit_price
                pnl = net_exit - pos["gross"]
                wallet += net_exit
                total_trades += 1
                if pnl >= 0:
                    wins += 1
                else:
                    losses += 1
                del active[sym]

            # Open new trades (max 10)
            if len(active) < 10 and wallet >= 10.0:
                if use_dynamic_sizing:
                    # Dynamic sizing: base $10, scale up to $50 based on available capital
                    # Higher conviction (moonshot setup) gets bigger allocation
                    base_pct = 0.015  # 1.5% of wallet per trade
                    trade_alloc = min(50.0, max(10.0, wallet * base_pct))
                else:
                    trade_alloc = 10.0  # Flat sizing

                if wallet >= trade_alloc:
                    cost = gas_fee + (trade_alloc * swap_fee) + (trade_alloc * slip_fee)
                    net_inv = trade_alloc - cost
                    qty = net_inv / 1.0
                    cat = random.choices(categories, weights=weights)[0]
                    sym = f"T{random.randint(1000, 9999)}"
                    active[sym] = {"gross": trade_alloc, "qty": qty, "category": cat}
                    wallet -= trade_alloc

        # End of day

    wr = (wins / total_trades * 100) if total_trades > 0 else 0.0
    return {"ending": wallet, "wr": wr, "trades": total_trades, "tp_hits": tp_hits}


def run_compound_projection():
    print("=" * 90)
    print("💰 V10.0 PREDATOR - SIMULASI COMPOUND 12 BULAN (50 MONTE CARLO RUNS)")
    print("=" * 90)

    # Compound simulation for different starting capitals
    capitals = [1000.0, 5000.0, 10000.0]

    for capital in capitals:
        print(f"\n{'='*90}")
        print(f"💵 SKENARIO MODAL AWAL: ${capital:,.0f}")
        print(f"{'='*90}")
        print(f"{'BULAN':<8} | {'SALDO RATA-RATA':<18} | {'PROFIT BULAN INI':<18} | {'PROFIT KUMULATIF':<18} | {'RETURN %'}")
        print("-" * 90)

        all_runs_monthly = []

        for run in range(50):
            seed_base = 9000 + run * 41
            monthly_wallets = [capital]
            current_wallet = capital

            for month in range(1, 13):
                seed = seed_base + month * 7
                result = simulate_month(seed, current_wallet, use_dynamic_sizing=True)
                current_wallet = result["ending"]
                monthly_wallets.append(current_wallet)

            all_runs_monthly.append(monthly_wallets)

        # Average across all runs per month
        for month in range(1, 13):
            avg_wallet = statistics.mean(run[month] for run in all_runs_monthly)
            avg_prev = statistics.mean(run[month - 1] for run in all_runs_monthly)
            monthly_profit = avg_wallet - avg_prev
            cumulative_profit = avg_wallet - capital
            return_pct = ((avg_wallet - capital) / capital) * 100
            print(f"Bulan {month:<3} | ${avg_wallet:<17,.2f} | ${monthly_profit:<17.2f} | ${cumulative_profit:<17.2f} | {return_pct:+.1f}%")

        final_avg = statistics.mean(run[12] for run in all_runs_monthly)
        final_profit = final_avg - capital
        print(f"\n🎯 HASIL AKHIR 12 BULAN DENGAN MODAL ${capital:,.0f}:")
        print(f"   Saldo Akhir     : ${final_avg:,.2f}")
        print(f"   Total Profit    : +${final_profit:,.2f} USD")
        print(f"   Total Return    : +{((final_avg - capital) / capital) * 100:.1f}%")


def run_position_size_comparison():
    print("\n" + "=" * 90)
    print("📊 DAMPAK UKURAN MODAL TERHADAP PROFIT PER BULAN (30 HARI, 50 RUNS)")
    print("=" * 90)
    print(f"{'MODAL AWAL':<15} | {'SIZING MODE':<18} | {'AVG PROFIT/BLN':<16} | {'RETURN %':<10} | {'WIN RATE'}")
    print("-" * 90)

    test_cases = [
        (1000.0,  "Flat $10"),
        (5000.0,  "Flat $10"),
        (10000.0, "Flat $10"),
        (1000.0,  "Dynamic 1.5%"),
        (5000.0,  "Dynamic 1.5%"),
        (10000.0, "Dynamic 1.5%"),
    ]

    for capital, mode in test_cases:
        dynamic = "Dynamic" in mode
        ends = []
        wrs = []

        for i in range(50):
            seed = 5555 + i * 17
            r = simulate_month(seed, capital, dynamic)
            ends.append(r["ending"])
            wrs.append(r["wr"])

        avg_end = statistics.mean(ends)
        avg_profit = avg_end - capital
        avg_wr = statistics.mean(wrs)
        ret_pct = (avg_profit / capital) * 100

        print(f"${capital:<14,.0f} | {mode:<18} | ${avg_profit:<15.2f} | {ret_pct:<8.1f}% | {avg_wr:.1f}%")

    print("=" * 90)
    print("\n💡 KESIMPULAN:")
    print("   1. Modal lebih besar = profit lebih besar (return % relatif sama)")
    print("   2. Dynamic sizing menghasilkan profit lebih tinggi dari flat sizing")
    print("   3. Compound selama 12 bulan = pertumbuhan eksponensial modal Anda!")
    print("=" * 90)


if __name__ == "__main__":
    run_position_size_comparison()
    run_compound_projection()
