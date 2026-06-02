# ============================================================================
# DEX PREDATOR - STRATEGY & FILTER CONFIGURATION
# ============================================================================
# Gunakan file ini untuk mengatur kelonggaran filter dan mode trading.
# Jangan letakkan API Keys di sini (biarkan di .env).

# --- PRODUCTION TRADING MODES ---
# Pilihan: 
#   OPTIMIZED       (WR 57% PnL +18%)
#   MOONSHOT        (WR 50% PnL +26%)
#   SCALPER         (WR 75% PnL +4.7%)
#   HOLY_GRAIL_75WR (WR 75-80% PnL +15%) -> Mode agresif TP awal 50%
TRADE_MODE = "OPTIMIZED"

# --- STRATEGY SCORING THRESHOLD ---
# Skor minimal yang dikeluarkan oleh engine predator_score
# BERSADARKAN HASIL SIMULASI: Dikembalikan ke 90 (Goldilocks Mode).
MIN_ENTRY_SCORE = 90

# --- DYNAMIC HIGH-FREQUENCY FILTERS (V26 OPTIMIZED) ---
# Filter untuk mengambil koin baru di detik-detik awal peluncuran:
MIN_LIQ = 5000        # Likuiditas minimal USD (Anti-Slippage)
MAX_LIQ = 500000      # Likuiditas maksimal USD (Anti-Koin Raksasa/Lamban)
MIN_MCAP = 5000       # Market Cap minimal USD
MIN_VOL_5M = 15000    # Volume transaksi 5 menit minimal USD (Wajib sangat tinggi!)
MIN_TRADES_5M = 50    # Jumlah transaksi total 5 menit minimal (Buy + Sell)

# Apakah wajib ada link Twitter/Website/Telegram di DexScreener?
# BERSADARKAN HASIL SIMULASI: FALSE (Karena 80% koin pemenang awal tidak memiliki link sosial!)
REQUIRE_SOCIALS = False
