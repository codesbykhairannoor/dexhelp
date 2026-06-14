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
TRADE_MODE = "SCALPER"

# --- STRATEGY SCORING THRESHOLD ---
# Skor minimal yang dikeluarkan oleh engine predator_score
# BERSADARKAN SUPER_BACKTEST: 80 (Karena kita berburu koin baru tanpa sosmed).
MIN_ENTRY_SCORE = 83  # LOWERED: After prolonged zero-win cycle with ultra-strict entry, we reduce threshold slightly to allow higher volume under improved TP/SL dynamics — prioritizing actionable edge over perfection

# --- DYNAMIC HIGH-FREQUENCY FILTERS (V26 OPTIMIZED) ---
# Filter untuk mengambil koin baru di detik-detik awal peluncuran:
MAX_AGE_MINUTES = 0.9  # LOOSENED: To account for blockchain propagation delay; entering between 48–54s proved fatal in multiple cycles, so we extend to 54s to capture ignition phase without missing entries
MIN_LIQ = 75000        # SLIGHTLY LOWERED: $80k+ is too restrictive post-consolidation; $75k ensures sufficient trade flow while maintaining slippage control
MAX_LIQ = 250000       # Tightened to focus on mid-volatility memecoins with room to run
MIN_MCAP = 2500        # Unchanged — still effective at noise filtration
MIN_VOL_5M = 90000     # Adjusted down from $100k to increase opportunity flow while staying above fake pumps
MIN_TRADES_5M = 30     # Reduced from 35 to prevent overfiltering during early pump formation

# Apakah wajib ada link Twitter/Website/Telegram di DexScreener?
# BERSADARKAN HASIL SIMULASI: FALSE (Karena 80% koin pemenang awal tidak memiliki link sosial!)
REQUIRE_SOCIALS = False
