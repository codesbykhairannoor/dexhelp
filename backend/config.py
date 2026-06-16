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
TRADE_MODE = "HIT_AND_RUN"  # Cycle 21: Post-volatility stabilization entry - entering at 5.0-6.0min after initial dump settles, using wider SL (18%) to survive normal wicks and extended time bomb (2.5min) for momentum confirmation

# --- STRATEGY SCORING THRESHOLD ---
# Skor minimal yang dikeluarkan oleh engine predator_score
# BERSADARKAN SUPER_BACKTEST: 80 (Karena kita berburu koin baru tanpa sosmed).
MIN_ENTRY_SCORE = 85  # CYCLE_21: Increased selectivity after consecutive SL hits - only highest conviction AI-vetted signals with strong Vibe Check scores

# --- DYNAMIC HIGH-FREQUENCY FILTERS (V26 OPTIMIZED) ---
# Filter untuk mengambil koin baru di detik-detik awal peluncuran:
MAX_AGE_MINUTES = 6.0  # CYCLE_21: Extended entry window to 5-6min - allows initial sniper dump to fully complete and organic accumulation to establish before entry
MIN_LIQ = 15000        # CYCLE_21: Raised slightly for better price stability - reduces slippage risk on entry/exit during volatile wicks
MAX_LIQ = 180000       # Tightened to avoid pools with artificial liquidity inflation
MIN_MCAP = 4000        # Lowered to access earlier-stage plays with higher upside potential
MIN_VOL_5M = 8000      # CYCLE_21: Moderate increase - ensures sufficient organic activity without relying solely on AI filtering for volume validation
MIN_TRADES_5M = 25      # Slightly raised to confirm emerging organic interest without relying on volume

# Apakah wajib ada link Twitter/Website/Telegram di DexScreener?
# BERSADARKAN HASIL SIMULASI: FALSE (Karena 80% koin pemenang awal tidak memiliki link sosial!)
REQUIRE_SOCIALS = False
