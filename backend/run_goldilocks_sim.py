import random
import time
import sys

# Fix encoding
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def simulate_goldilocks(days=30, mode="GOLDILOCKS"):
    capital = 1000.0
    wins = 0
    losses = 0
    trade_size = 10.0
    
    # Probabilities based on real data (18 random BirdEye tokens)
    # 66% Win Rate if we don't buy Trash / Giant coins.
    # Sniper Mode = Very few trades (e.g. 2 per day) but misses 80% of moonshots (because they lack socials)
    # Goldilocks Mode = Normal trades (e.g. 10 per day), captures the 66% win rate safely.
    
    if mode == "SNIPER":
        trades_per_day = 2
        win_rate = 0.50 # Misses the organic fast moonshots
    else:
        trades_per_day = 10
        win_rate = 0.65 # V17.0 true backtest rate
        
    for d in range(days):
        for t in range(trades_per_day):
            if capital < 0:
                break
                
            is_win = random.random() < win_rate
            
            if is_win:
                # 80% sold at +30%, 20% sold at +3% (Runner BE-Lock)
                # Weighted PnL = (0.8 * 0.30) + (0.2 * 0.03) = 0.24 + 0.006 = 0.246 (+24.6%)
                pnl = trade_size * 0.246
                wins += 1
            else:
                # SL hit at 15% (with slippage, effectively 18-20% loss on some, let's say -17% average)
                pnl = -trade_size * 0.17
                losses += 1
                
            capital += pnl
            
    total = wins + losses
    actual_wr = (wins / total * 100) if total > 0 else 0
    
    return {
        "mode": mode,
        "capital": capital,
        "pnl": capital - 1000.0,
        "trades": total,
        "win_rate": actual_wr
    }

print("="*80)
print("📊 SIMULASI 30 HARI: V18.0 SNIPER vs V18.1 GOLDILOCKS ZONE")
print("="*80)
print("Skenario: $10 per trade (Partial TP 80% di +30%, Runner 20%)")
print("-" * 80)

for mode in ["SNIPER", "GOLDILOCKS"]:
    avg_pnl = 0
    avg_wr = 0
    avg_trades = 0
    runs = 1000
    for _ in range(runs):
        res = simulate_goldilocks(mode=mode)
        avg_pnl += res["pnl"]
        avg_wr += res["win_rate"]
        avg_trades += res["trades"]
        
    avg_pnl /= runs
    avg_wr /= runs
    avg_trades /= runs
    
    print(f"MODE: {mode:<15} | TRADES: {avg_trades:<5.0f} | WIN RATE: {avg_wr:<5.1f}% | EST PNL 30 HARI: ${avg_pnl:+.2f}")
    
print("="*80)
