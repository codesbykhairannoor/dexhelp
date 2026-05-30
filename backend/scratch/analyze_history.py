import json
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PORTFOLIO_FILE = os.path.join(CURRENT_DIR, "paper_portfolio.json")

def analyze():
    with open(PORTFOLIO_FILE, "r") as f:
        data = json.load(f)
        
    history = data.get("trade_history", [])
    wins = 0
    losses = 0
    total_pnl_pct_wins = 0
    total_pnl_pct_losses = 0
    
    for t in history:
        pnl = t.get("pnl_pct", 0)
        if pnl > 0:
            wins += 1
            total_pnl_pct_wins += pnl
        else:
            losses += 1
            total_pnl_pct_losses += pnl
            
    print(f"Total Trades: {len(history)}")
    print(f"Wins: {wins} ({(wins/len(history))*100 if history else 0:.2f}%)")
    print(f"Losses: {losses} ({(losses/len(history))*100 if history else 0:.2f}%)")
    print(f"Avg Win: {total_pnl_pct_wins/wins if wins else 0:.2f}%")
    print(f"Avg Loss: {total_pnl_pct_losses/losses if losses else 0:.2f}%")
    
if __name__ == "__main__":
    analyze()
