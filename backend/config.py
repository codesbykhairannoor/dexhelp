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
MIN_ENTRY_SCORE = 75  # REBALANCED: Frekuensi sudah tercapai, sekarang tingkatkan kualitas entry untuk hindari rug/dump

# --- DYNAMIC HIGH-FREQUENCY FILTERS (V26 OPTIMIZED) ---
# Filter untuk mengambil koin baru di detik-detik awal peluncuran:
MAX_AGE_MINUTES = 3  # KURANGI: Koin >3 menit sering kali sudah pump & dump, butuh kesegaran untuk momentum
MIN_LIQ = 10000       # KRITIS: $1.8k menyebabkan slippage parah (bukti loss -34% pada SL 10%). $10k wajib untuk eksekusi aman
MAX_LIQ = 450000      # Slightly tighter: Hindari koin yang mulai melambat karena ukuran
MIN_MCAP = 1800       # Turun sedikit untuk cap bottoming new launches
MIN_VOL_5M = 25000    # TINGKATKAN: $7k terlalu mudah dimanipulasi whale. $25k validasi momentum organik kuat
MIN_TRADES_5M = 20    # Turun ke 20: Validasi partisipasi user tetap ada tanpa batasi terlalu ketat

# Apakah wajib ada link Twitter/Website/Telegram di DexScreener?
# BERSADARKAN HASIL SIMULASI: FALSE (Karena 80% koin pemenang awal tidak memiliki link sosial!)
REQUIRE_SOCIALS = False
