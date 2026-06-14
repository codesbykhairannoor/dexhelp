# ============================================================================
# DEX PREDATOR - STRATEGY & FILTER CONFIGURATION
# ============================================================================
# Gunakan file ini untuk mengatur kelonggaran filter dan mode trading.
# Jangan letakkan API Keys di sini (biarkan di .env).

# --- PRODUCTION TRADING MODES ---
# Pilihan: 
#   HIT_AND_RUN     (Konsisten Cuan Harian: Langsung TP 100% di +20%, tidak rakus)
#   RUNNER          (Murni Sniper: TP 50% di +30%, sisa dibiarkan Moonshot)
#   OPTIMIZED       (WR 57% PnL +18%)
#   MOONSHOT        (WR 50% PnL +26%)
#   SCALPER         (WR 75% PnL +4.7%)
#   HOLY_GRAIL_75WR (WR 75-80% PnL +15%) -> Mode agresif TP awal 50%
TRADE_MODE = "HIT_AND_RUN"

# --- STRATEGY SCORING THRESHOLD ---
# Skor minimal yang dikeluarkan oleh engine predator_score
# BERSADARKAN SUPER BACKTEST: 80 (Karena kita berburu koin baru tanpa sosmed).
MIN_ENTRY_SCORE = 85  # RAISED: Revert looseness — after failed scalper shift, we now demand higher signal quality to filter false pumps amid increasing noise

# --- DYNAMIC HIGH-FREQUENCY FILTERS (V26 OPTIMIZED) ---
# Filter untuk mengambil koin baru di detik-detik awal peluncuran:
MAX_AGE_MINUTES = 0.9  # TIGHTENED: Enter earlier in the pump lifecycle — 1.1min was too late, allowing distribution to begin before entry
MIN_LIQ = 75000        # RAISED: Increase pool depth requirement to dominate exit execution and reduce slippage below -10%
MAX_LIQ = 300000       # Lowered to avoid coins attracting institutional-sized liquidity which dampens volatility
MIN_MCAP = 2500        # Unchanged — still effective at noise filtration
MIN_VOL_5M = 95000     # RAISED: Only accept extreme volume momentum, confirming retail FOMO phase is active
MIN_TRADES_5M = 30     # MAXED: Highest crowd validation threshold yet — ensures broad participation, not just whale-driven pumps

# Apakah wajib ada link Twitter/Website/Telegram di DexScreener?
# BERSADARKAN HASIL SIMULASI: FALSE (Karena 80% koin pemenang awal tidak memiliki link sosial!)
REQUIRE_SOCIALS = False
