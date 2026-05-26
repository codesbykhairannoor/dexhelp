#!/bin/bash
echo "=========================================================="
echo "🔧 DEX PREDATOR - VPS AUTO-FIX SCRIPT"
echo "=========================================================="
echo "Script ini akan memperbaiki masalah 'No module named requests'"
echo "dan memastikan PM2 menggunakan Virtual Environment yang benar."
echo ""

# 1. Masuk ke direktori backend
cd /home/ubuntu/dexhelp/backend || { echo "Direktori backend tidak ditemukan!"; exit 1; }

# 2. Hentikan dan hapus instance PM2 lama yang salah
echo "[1/4] Menghapus instance PM2 lama..."
pm2 delete bot-paper 2>/dev/null
pm2 delete bot-real 2>/dev/null

# 3. Pastikan virtual environment aktif dan dependencies terinstall
echo "[2/4] Menginstall ulang dependencies di virtual environment..."
cd /home/ubuntu/dexhelp
source venv/bin/activate
pip install -r requirements.txt

# 4. Jalankan ulang bot menggunakan interpreter Python dari venv
echo "[3/4] Menyalakan ulang bot dengan VENV Interpreter..."
cd /home/ubuntu/dexhelp/backend

# Jalankan Paper Trader (Ganti ke live_real_trader.py kalau mau live)
pm2 start live_paper_trader.py --name "bot-paper" --interpreter ../venv/bin/python

# 5. Simpan konfigurasi PM2 agar jalan otomatis saat server restart
echo "[4/4] Menyimpan state PM2..."
pm2 save

echo "=========================================================="
echo "✅ PERBAIKAN SELESAI!"
echo "Sekarang Anda bisa mengecek log dengan perintah:"
echo "pm2 logs bot-paper"
echo "=========================================================="
