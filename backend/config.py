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
MIN_ENTRY_SCORE = 85  # LOWERED: After strict filters still resulted in -100% WR, we now prioritize trade flow. High conviction not enough if execution fails.

# --- DYNAMIC HIGH-FREQUENCY FILTERS (V26 OPTIMIZED) ---
# Filter untuk mengambil koin baru di detik-detik awal peluncuran:
MAX_AGE_MINUTES = 1.0  # TIGHTENED: From 1.2 to 1.0 minute — re-focus on ultra-early entry within first 60 seconds of launch, avoiding distribution phase
MIN_LIQ = 65000        # RAISED: From $60k to $65k to enforce deeper liquidity pools, minimizing slippage on exit after DICKFACE -34% failure
MAX_LIQ = 380000       # Lowered slightly to avoid coins with fading momentum post-initial spike
MIN_MCAP = 2500        # Increased to filter out more noise and focus on slightly established caps
MIN_VOL_5M = 85000     # RAISED: From $80k to $85k to require even stronger volume confirmation, reducing false breakouts
MIN_TRADES_5M = 25     # Increased to ensure high trader participation — real demand signal

# Apakah wajib ada link Twitter/Website/Telegram di DexScreener?
# BERSADARKAN HASIL SIMULASI: FALSE (Karena 80% koin pemenang awal tidak memiliki link sosial!)
REQUIRE_SOCIALS = False
