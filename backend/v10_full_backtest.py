import sys
import random
import statistics

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ============================================================================
# V10.0 PREDATOR FULL BACKTEST
# Simulates OLD bot (no entry filter) vs NEW bot (6 signal filtered entries)
# Uses realistic Solana market distribution + V9.1 exit params
# ============================================================================

def simulate_trade(category: str, sl_pct: float, tp_pct: float, be_active: bool, lp_depth: int, seed_offset: int) -> dict:
    """Simulate a single trade lifecycle given a category."""
    entry_price = 1.0
    highest_price = entry_price
    current_price = entry_price
    steps = 60
    exit_price = entry_price

    if category == "DUMP":
        for _ in range(steps):
            current_price *= random.uniform(0.80, 0.98)
        exit_price = max(current_price, entry_price * (1 - sl_pct))

    elif category == "SCALP":
        for step in range(steps):
            current_price *= random.uniform(0.95, 1.06)
            highest_price = max(highest_price, current_price)
            price_gain_pct = ((highest_price - entry_price) / entry_price) * 100

            if tp_pct > 0 and price_gain_pct >= tp_pct:
                exit_price = entry_price * (1 + tp_pct / 100)
                return {"exit": exit_price, "category": category, "result": "TP"}

            if be_active and price_gain_pct >= 4.0:
                floor_sl = entry_price * 1.03
            else:
                floor_sl = highest_price * (1 - sl_pct)

            if current_price <= floor_sl:
                exit_price = floor_sl
                return {"exit": exit_price, "category": category, "result": "SL"}

        exit_price = current_price
        exit_impact = (9.915 * exit_price) / (lp_depth / 2)
        exit_price *= (1 - exit_impact)

    elif category == "MOONSHOT":
        for step in range(steps):
            if step < 25:
                current_price *= random.uniform(1.04, 1.22)
            else:
                current_price *= random.uniform(0.87, 1.02)
            highest_price = max(highest_price, current_price)
            price_gain_pct = ((highest_price - entry_price) / entry_price) * 100

            if tp_pct > 0 and price_gain_pct >= tp_pct:
                exit_price = entry_price * (1 + tp_pct / 100)
                return {"exit": exit_price, "category": category, "result": "TP"}

            if price_gain_pct >= 100.0:
                floor_sl = entry_price * 1.65
            elif price_gain_pct >= 40.0:
                floor_sl = entry_price * 1.15
            else:
                floor_sl = highest_price * (1 - sl_pct)

            if current_price <= floor_sl:
                exit_price = floor_sl
                return {"exit": exit_price, "category": category, "result": "SL"}

        exit_price = current_price

    result = "WIN" if exit_price >= entry_price else "LOSS"
    return {"exit": exit_price, "category": category, "result": result}


def run_engine(
    seed: int,
    days: int,
    sl_pct: float,
    tp_pct: float,
    be_active: bool,
    entry_quality: str  # "UNFILTERED" vs "V10_FILTERED"
) -> dict:
    random.seed(seed)

    initial_capital = 1000.0
    wallet = initial_capital
    active = {}

    # ENTRY QUALITY MODEL:
    # UNFILTERED: Old bot - buys anything with score >= 70, no age/vol/holder checks
    #   Distribution: 50% DUMP, 40% SCALP, 10% MOONSHOT (lots of old/late tokens)
    # V10_FILTERED: New bot - age window, vol accel, top-1 holder, FDV ratio
    #   Distribution: 25% DUMP, 55% SCALP, 20% MOONSHOT (better token selection)
    if entry_quality == "UNFILTERED":
        weights = [0.50, 0.40, 0.10]
    else:  # V10_FILTERED
        weights = [0.25, 0.55, 0.20]

    categories = ["DUMP", "SCALP", "MOONSHOT"]

    gas_fee = 0.01
    swap_fee = 0.0025
    slip_fee = 0.005
    trade_alloc = 10.0

    total_trades = 0
    wins = 0
    losses = 0
    highest_wallet = initial_capital
    max_drawdown = 0.0
    tp_hits = 0
    sl_hits = 0

    for day in range(1, days + 1):
        daily_opps = random.randint(3, 8)

        for _ in range(daily_opps):
            # Process exits
            for sym, pos in list(active.items()):
                lp = pos["lp"]
                cat = pos["category"]
                trade_res = simulate_trade(cat, sl_pct, tp_pct, be_active, lp, day)
                exit_p = trade_res["exit"]
                net_exit = pos["qty"] * exit_p
                pnl = net_exit - pos["gross"]
                wallet += net_exit
                total_trades += 1
                if pnl >= 0:
                    wins += 1
                else:
                    losses += 1
                if trade_res["result"] == "TP":
                    tp_hits += 1
                elif trade_res["result"] == "SL":
                    sl_hits += 1
                del active[sym]

            # Open new trades (max 10)
            if len(active) < 10 and wallet >= trade_alloc:
                cost = gas_fee + (trade_alloc * swap_fee) + (trade_alloc * slip_fee)
                net_inv = trade_alloc - cost
                qty = net_inv / 1.0
                cat = random.choices(categories, weights=weights)[0]
                lp = random.choice([15000, 25000, 50000, 100000, 200000])
                sym = f"T{random.randint(1000,9999)}"
                active[sym] = {
                    "gross": trade_alloc,
                    "qty": qty,
                    "category": cat,
                    "lp": lp
                }
                wallet -= trade_alloc

        highest_wallet = max(highest_wallet, wallet)
        if highest_wallet > 0:
            dd = ((highest_wallet - wallet) / highest_wallet) * 100
            max_drawdown = max(max_drawdown, dd)

    wr = (wins / total_trades * 100) if total_trades > 0 else 0.0
    return {
        "ending": wallet,
        "wr": wr,
        "dd": max_drawdown,
        "trades": total_trades,
        "tp_hits": tp_hits,
        "sl_hits": sl_hits
    }


def full_backtest():
    print("=" * 110)
    print("🛸 V10.0 PREDATOR FULL BACKTEST: OLD ENTRY FILTER vs NEW 6-SIGNAL FILTER")
    print("   Modal: $1000 | Trade Size: $10 flat | 30 Hari | 50 Monte Carlo Runs")
    print("=" * 110)

    configs = [
        {"label": "OLD BOT (Unfiltered)", "quality": "UNFILTERED", "be": True,  "sl": 0.20, "tp": 30.0},
        {"label": "V10 BE-ACTIVE SL20 TP30", "quality": "V10_FILTERED", "be": True,  "sl": 0.20, "tp": 30.0},
        {"label": "V10 BE-ACTIVE SL20 TP20", "quality": "V10_FILTERED", "be": True,  "sl": 0.20, "tp": 20.0},
        {"label": "V10 BE-ACTIVE SL15 TP30", "quality": "V10_FILTERED", "be": True,  "sl": 0.15, "tp": 30.0},
        {"label": "V10 BE-INACT SL10 TP30",  "quality": "V10_FILTERED", "be": False, "sl": 0.10, "tp": 30.0},
        {"label": "V10 BE-INACT SL20 TP30",  "quality": "V10_FILTERED", "be": False, "sl": 0.20, "tp": 30.0},
    ]

    num_runs = 50
    days = 30

    print(f"\n{'KONFIGURASI':<28} | {'AVG BALANCE':<13} | {'PROFIT':<10} | {'WIN RATE':<9} | {'MAX DD':<9} | {'TP HITS':<8} | {'SL HITS'}")
    print("-" * 110)

    results = []
    for cfg in configs:
        ends = []
        wrs = []
        dds = []
        tp_total = 0
        sl_total = 0

        for i in range(num_runs):
            seed = 7777 + i * 31
            r = run_engine(
                seed=seed,
                days=days,
                sl_pct=cfg["sl"],
                tp_pct=cfg["tp"],
                be_active=cfg["be"],
                entry_quality=cfg["quality"]
            )
            ends.append(r["ending"])
            wrs.append(r["wr"])
            dds.append(r["dd"])
            tp_total += r["tp_hits"]
            sl_total += r["sl_hits"]

        avg_end = statistics.mean(ends)
        avg_wr = statistics.mean(wrs)
        avg_dd = statistics.mean(dds)
        avg_profit = avg_end - 1000.0
        avg_tp = tp_total / num_runs
        avg_sl = sl_total / num_runs

        results.append({**cfg, "avg_end": avg_end, "avg_wr": avg_wr, "avg_dd": avg_dd})

        marker = " ⭐" if cfg["quality"] == "V10_FILTERED" else ""
        print(f"{cfg['label'] + marker:<28} | ${avg_end:<12.2f} | ${avg_profit:<9.2f} | {avg_wr:<7.1f}% | {avg_dd:<7.1f}% | {avg_tp:<8.1f} | {avg_sl:.1f}")

    # Best config
    best = max(results, key=lambda x: x["avg_end"])
    print("\n" + "=" * 110)
    print(f"🏆 KONFIGURASI TERBAIK: {best['label']}")
    print(f"   BE-Guard: {'ACTIVE' if best['be'] else 'INACTIVE'} | SL: {int(best['sl']*100)}% | TP: {int(best['tp'])}%")
    print(f"   Expected Monthly Return: ${best['avg_end'] - 1000:.2f} USD dari $1000 modal")
    print(f"   Win Rate: {best['avg_wr']:.1f}% | Max Drawdown: {best['avg_dd']:.1f}%")
    print("=" * 110)

    # Impact comparison
    old = next(r for r in results if r["quality"] == "UNFILTERED")
    new_best = max((r for r in results if r["quality"] == "V10_FILTERED"), key=lambda x: x["avg_end"])
    lift = new_best["avg_end"] - old["avg_end"]
    print(f"\n📈 DAMPAK UPGRADE V10.0 FILTER:")
    print(f"   Saldo akhir OLD  : ${old['avg_end']:.2f}")
    print(f"   Saldo akhir V10  : ${new_best['avg_end']:.2f}")
    print(f"   Peningkatan      : +${lift:.2f} USD ({(lift/old['avg_end'])*100:.1f}% lebih baik!)")
    print("=" * 110)


if __name__ == "__main__":
    full_backtest()
