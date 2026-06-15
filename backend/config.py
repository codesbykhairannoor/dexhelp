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
TRADE_MODE = "SCALPER"  # Shift to SCALPER: Capture momentum waves missed by rigid HIT_AND_RUN; use 25% TP to exit before second-leg dump

# --- STRATEGY SCORING THRESHOLD ---
# Skor minimal yang dikeluarkan oleh engine predator_score
# BERSADARKAN SUPER_BACKTEST: 80 (Karena kita berburu koin baru tanpa sosmed).
MIN_ENTRY_SCORE = 83  # Lowered: Previous high score requirement filtered out viable entries; allow strong signals with slight variance

# --- DYNAMIC HIGH-FREQUENCY FILTERS (V26 OPTIMIZED) ---
# Filter untuk mengambil koin baru di detik-detik awal peluncuran:
MAX_AGE_MINUTES = 5.0  # MAJOR LOOSEN: Per DEGEN WISDOM — buying at <2min with high volume leads to honeypots. Wait 5+ mins for dust to settle, volume to stabilize organically
MIN_LIQ = 80000        # Lowered: Allow earlier participation in genuine low-liquidity pumps that grow organically
MAX_LIQ = 300000       # Raised: Permit slightly larger plays post-consolidation, targeting momentum continuation
MIN_MCAP = 3000        # Slight loosen: Maintain sensitivity to early caps with real traction
MIN_VOL_5M = 60000     # Reduced: Focus on organic volume buildup, not artificial hype walls
MIN_TRADES_5M = 30     # Slight loosen: Ensure sufficient trader consensus without overfitting to noise

# Apakah wajib ada link Twitter/Website/Telegram di DexScreener?
# BERSADARKAN HASIL SIMULASI: FALSE (Karena 80% koin pemenang awal tidak memiliki link sosial!)
REQUIRE_SOCIALS = False
