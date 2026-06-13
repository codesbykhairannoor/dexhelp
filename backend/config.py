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
MIN_ENTRY_SCORE = 87  # INCREASED: Raise conviction bar slightly after repeated SL hits. Balance between quality and quantity.

# --- DYNAMIC HIGH-FREQUENCY FILTERS (V26 OPTIMIZED) ---
# Filter untuk mengambil koin baru di detik-detik awal peluncuran:
MAX_AGE_MINUTES = 1.2  # NEW: Tighten from 1.5 to 1.2 minutes — catch coins earlier in pump phase without being too late
MIN_LIQ = 60000       # RAISED: From $50k to $60k to further reduce slippage risk after DICKFACE -34% loss despite previous fix
MAX_LIQ = 400000      # Slightly lower to avoid mid-sized coins losing momentum
MIN_MCAP = 2000       # Slight increase to filter out extremely low-cap noise
MIN_VOL_5M = 80000    # RAISED: From $75k to $80k to ensure stronger, cleaner momentum entering the trade
MIN_TRADES_5M = 22    # Increase to confirm higher participation and organic traction

# Apakah wajib ada link Twitter/Website/Telegram di DexScreener?
# BERSADARKAN HASIL SIMULASI: FALSE (Karena 80% koin pemenang awal tidak memiliki link sosial!)
REQUIRE_SOCIALS = False
