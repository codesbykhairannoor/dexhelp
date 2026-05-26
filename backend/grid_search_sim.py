import itertools
import random
import multiprocessing

def run_simulation(params):
    req_socials, min_liq, min_score, trade_mode = params
    
    # 1. Tentukan Probabilitas Market Berdasarkan Filter
    if not req_socials and min_liq <= 1000:
        trades_per_day = 30
        weights = [0.90, 0.08, 0.02]  # 90% Rugpull, 8% Scalp, 2% Moonshot
    elif req_socials and min_liq >= 3000:
        trades_per_day = 5
        weights = [0.60, 0.30, 0.10]
    elif req_socials and min_liq < 3000:
        trades_per_day = 10
        weights = [0.75, 0.20, 0.05]
    else:
        trades_per_day = 20
        weights = [0.85, 0.12, 0.03]
        
    # Min Score mempengaruhi kualitas trade (mengurangi jumlah trade & memperbaiki win rate secara linear)
    if min_score >= 80:
        trades_per_day = max(1, int(trades_per_day * (1 - (min_score-70)*0.03))) # Makin tinggi score makin jarang trade
        improvement = (min_score - 70) * 0.015 # Score 90 = 0.30 improvement
        weights[0] = max(0.1, weights[0] - improvement)
        weights[1] += improvement * 0.7
        weights[2] += improvement * 0.3
    
    # Normalisasi bobot
    total_w = sum(weights)
    weights = [w/total_w for w in weights]
    
    # 2. Setup Mode Trading
    if trade_mode == "SCALPER":
        tp_pct = 0.15
        tp_amount = 1.0 # Jual 100% di TP
        sl_pct = 0.15
    elif trade_mode == "HOLY_GRAIL":
        tp_pct = 0.15
        tp_amount = 0.50 # Jual 50%
        sl_pct = 0.15
    elif trade_mode == "MOONSHOT":
        tp_pct = 0.50
        tp_amount = 0.50
        sl_pct = 0.30
    else:
        tp_pct, tp_amount, sl_pct = 0.20, 0.80, 0.20
        
    # 3. Jalankan 30 Hari Simulasi
    days = 30
    capital = 1000.0
    allocation_pct = 0.01  # 1% per trade ($10)
    
    wins = 0
    losses = 0
    
    for _ in range(days):
        if capital <= 0: break
        for _ in range(trades_per_day):
            trade_size = 10.0 # Fixed $10 per trade
            
            outcome = random.choices(["DUMP", "SCALP", "MOONSHOT"], weights=weights)[0]
            
            pnl_usd = 0
            # Model Slippage: Saat rugpull (DUMP), API delay membuat kita telat cut loss
            if outcome == "DUMP":
                actual_sl = sl_pct + 0.20  # Telat 20% karena slippage
                pnl_usd = -trade_size * actual_sl
                losses += 1
            elif outcome == "SCALP":
                # Kena TP lalu sisa SL di BE
                if trade_mode == "SCALPER":
                    pnl_usd = trade_size * tp_pct
                elif trade_mode == "HOLY_GRAIL":
                    # 50% TP, 50% BE
                    pnl_usd = (trade_size * 0.5 * tp_pct) + 0 
                elif trade_mode == "MOONSHOT":
                    # Gak kena TP (karena butuh 50%), malah kena SL
                    pnl_usd = -trade_size * sl_pct
                wins += 1
            elif outcome == "MOONSHOT":
                if trade_mode == "SCALPER":
                    pnl_usd = trade_size * tp_pct # Cuma dapat kecil
                elif trade_mode == "HOLY_GRAIL":
                    # 50% TP, 50% Runner sampai 100%
                    pnl_usd = (trade_size * 0.5 * tp_pct) + (trade_size * 0.5 * 1.0)
                elif trade_mode == "MOONSHOT":
                    # 50% TP di 50%, 50% di 200%
                    pnl_usd = (trade_size * 0.5 * 0.50) + (trade_size * 0.5 * 2.0)
                wins += 1
                
            capital += pnl_usd
            
    total_trades = wins + losses
    win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
    return {
        "params": params,
        "capital": capital,
        "pnl": capital - 1000.0,
        "trades": total_trades,
        "win_rate": win_rate
    }

if __name__ == "__main__":
    req_socials_opts = [True]
    min_liq_opts = [3000, 5000, 10000, 20000]
    min_score_opts = [80, 85, 90, 95]
    trade_mode_opts = ["HOLY_GRAIL", "OPTIMIZED"]
    
    combinations = list(itertools.product(req_socials_opts, min_liq_opts, min_score_opts, trade_mode_opts))
    
    print(f"🔬 Memulai Grid Search: {len(combinations)} Skenario...")
    
    results = []
    # Jalankan simulasi (kita loop 10x per kombinasi untuk average)
    for combo in combinations:
        avg_pnl = 0
        avg_wr = 0
        avg_trades = 0
        for _ in range(20): # Monte carlo 20 paths per combo
            res = run_simulation(combo)
            avg_pnl += res["pnl"]
            avg_wr += res["win_rate"]
            avg_trades += res["trades"]
        
        results.append({
            "socials": combo[0],
            "liq": combo[1],
            "score": combo[2],
            "mode": combo[3],
            "avg_pnl": avg_pnl / 20,
            "avg_wr": avg_wr / 20,
            "avg_trades": avg_trades / 20
        })
        
    # Sort berdasarkan PnL terbaik
    results.sort(key=lambda x: x["avg_pnl"], reverse=True)
    
    print("\n🏆 TOP 5 SKENARIO TERBAIK (30 HARI):")
    print("-" * 100)
    print(f"{'SOSIAL':<8} | {'MIN LIQ':<8} | {'SCORE':<5} | {'MODE':<12} | {'TRADES':<8} | {'WIN RATE':<8} | {'EST PnL (USD)'}")
    print("-" * 100)
    for r in results[:5]:
        soc = "YES" if r["socials"] else "NO"
        print(f"{soc:<8} | ${r['liq']:<7} | {r['score']:<5} | {r['mode']:<12} | {r['avg_trades']:<8.1f} | {r['avg_wr']:<7.1f}% | ${r['avg_pnl']:+.2f}")
        
    print("\n💀 TOP 5 SKENARIO TERBURUK:")
    print("-" * 100)
    for r in results[-5:]:
        soc = "YES" if r["socials"] else "NO"
        print(f"{soc:<8} | ${r['liq']:<7} | {r['score']:<5} | {r['mode']:<12} | {r['avg_trades']:<8.1f} | {r['avg_wr']:<7.1f}% | ${r['avg_pnl']:+.2f}")
