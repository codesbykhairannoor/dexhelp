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
TRADE_MODE = "HIT_AND_RUN"  # Cycle 17: Wider SL (15%) absorbs memecoin volatility; higher TP (25%) captures stronger momentum; tighter entry filters reduce trap exposure

# --- STRATEGY SCORING THRESHOLD ---
# Skor minimal yang dikeluarkan oleh engine predator_score
# BERSADARKAN SUPER_BACKTEST: 80 (Karena kita berburu koin baru tanpa sosmed).
MIN_ENTRY_SCORE = 85  # Tighten: Previous 79 score allowed weak setups that hit SL immediately; require stronger conviction signals after 2 consecutive losses

# --- DYNAMIC HIGH-FREQUENCY FILTERS (V26 OPTIMIZED) ---
# Filter untuk mengambil koin baru di detik-detik awal peluncuran:
MAX_AGE_MINUTES = 4.0  # ADAPT: 6min window catches second-wave dumps; enter 2-4min window where organic momentum establishes before consolidation trap phase
MIN_LIQ = 120000       # Raised: After 2 SL hits, require stronger liquidity foundation to reduce slippage and rug risk on entry/exit
MAX_LIQ = 320000       # Raised: Permit slightly larger plays post-consolidation, targeting momentum continuation
MIN_MCAP = 3000        # Slight loosen: Maintain sensitivity to early caps with real traction
MIN_VOL_5M = 75000     # Raised: Filter out weak volume coins that lack sustained momentum; require genuine trading interest to avoid instant dumps
MIN_TRADES_5M = 20     # Loosen: Accept lower trade count threshold to increase entry opportunities in surviving organic pumps

# Apakah wajib ada link Twitter/Website/Telegram di DexScreener?
# BERSADARKAN HASIL SIMULASI: FALSE (Karena 80% koin pemenang awal tidak memiliki link sosial!)
REQUIRE_SOCIALS = False
