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
TRADE_MODE = "HOLY_GRAIL_75WR"

# --- STRATEGY SCORING THRESHOLD ---
# Skor minimal yang dikeluarkan oleh engine predator_score
# Semakin rendah, semakin rajin trade (tapi risiko tinggi).
# BERSADARKAN HASIL SIMULASI (GRID SEARCH): Score 90 adalah yang paling stabil dan profitable.
MIN_ENTRY_SCORE = 90

# --- DYNAMIC HIGH-FREQUENCY FILTERS (V26 OPTIMIZED) ---
# Filter untuk mengambil koin baru di detik-detik awal peluncuran:
MIN_LIQ = 3000        # Likuiditas minimal USD ($3000 untuk menghindari instan rugpull)
MIN_MCAP = 10000      # Market Cap minimal USD
MIN_VOL_5M = 500      # Volume transaksi 5 menit minimal USD
MIN_TRADES_5M = 15    # Jumlah transaksi total 5 menit minimal (Buy + Sell)

# Apakah wajib ada link Twitter/Website/Telegram di DexScreener?
# BERSADARKAN HASIL SIMULASI: WAJIB TRUE! Token tanpa sosial 98% berujung kerugian masif.
REQUIRE_SOCIALS = True
