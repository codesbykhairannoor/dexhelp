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
TRADE_MODE = "HIT_AND_RUN"  # Cycle 20: Adaptive strike on post-sniper volatility compression - entering at 3.5-4.5min after fakeout washout, using AI-vetted low-volume signals with moderate SL and timed precision exit

# --- STRATEGY SCORING THRESHOLD ---
# Skor minimal yang dikeluarkan oleh engine predator_score
# BERSADARKAN SUPER_BACKTEST: 80 (Karena kita berburu koin baru tanpa sosmed).
MIN_ENTRY_SCORE = 82  # CYCLE_20: Slight relaxation to increase trade flow after zero-win cycle; DeepSeek AI now handles scam filtering

# --- DYNAMIC HIGH-FREQUENCY FILTERS (V26 OPTIMIZED) ---
# Filter untuk mengambil koin baru di detik-detik awal peluncuran:
MAX_AGE_MINUTES = 4.5  # CYCLE_20: Optimized entry window — after initial dump (2.5min) but before full consolidation (5min), targets compression breakout
MIN_LIQ = 12000        # CYCLE_20: Lowered slightly to capture organic low-liquidity movers that pass AI 'Vibe Check'
MAX_LIQ = 180000       # Tightened to avoid pools with artificial liquidity inflation
MIN_MCAP = 4000        # Lowered to access earlier-stage plays with higher upside potential
MIN_VOL_5M = 6000      # Further reduced — confidence in DeepSeek prevents rug risk, enabling early detection of non-wash trades
MIN_TRADES_5M = 25      # Slightly raised to confirm emerging organic interest without relying on volume

# Apakah wajib ada link Twitter/Website/Telegram di DexScreener?
# BERSADARKAN HASIL SIMULASI: FALSE (Karena 80% koin pemenang awal tidak memiliki link sosial!)
REQUIRE_SOCIALS = False
