#!/bin/bash
# ===========================================================================
#  SOLANA DEX PREDATOR - UBUNTU VPS AUTOMATED DEPLOYMENT SCRIPT
# ===========================================================================

# Ensure the script is run as root
if [ "$EUID" -ne 0 ]; then
  echo "❌ Please run this script with sudo or as root: sudo bash deploy_vps.sh"
  exit 1
fi

PROJECT_DIR="/opt/dexhelp"
GITHUB_REPO="https://github.com/codesbykhairannoor/dexhelp.git"

echo "========================================================================="
echo "⚙️  Starting Automated VPS Deployment Sequence for Ubuntu..."
echo "========================================================================="

# 1. Update system package index
echo "🔄 Updating system package index..."
apt-get update -y && apt-get upgrade -y

# 2. Install required dependencies
echo "📦 Installing required dependencies (Git, Python3, Pip, Venv)..."
apt-get install -y git python3 python3-pip python3-venv python3-dev curl build-essential

# 3. Provision project directory and clone code
if [ -d "$PROJECT_DIR" ]; then
  echo "📂 Project directory already exists at $PROJECT_DIR. Pulling latest code..."
  cd "$PROJECT_DIR"
  git reset --hard
  git pull origin main
else
  echo "📂 Creating project directory at $PROJECT_DIR and cloning repository..."
  git clone "$GITHUB_REPO" "$PROJECT_DIR"
  cd "$PROJECT_DIR"
fi

# 4. Set up Python Virtual Environment
echo "🐍 Setting up Python Virtual Environment (.venv)..."
python3 -m venv .venv
source .venv/bin/activate

# 5. Install Python dependencies
echo "📦 Installing Python package requirements..."
if [ -f "backend/requirements.txt" ]; then
  pip install --upgrade pip
  pip install -r backend/requirements.txt
elif [ -f "requirements.txt" ]; then
  pip install --upgrade pip
  pip install -r requirements.txt
else
  echo "⚠️  No requirements.txt found. Installing basic packages manually..."
  pip install --upgrade pip
  pip install requests python-dotenv
fi

# 6. Initialize local environment config template (.env)
if [ ! -f "backend/.env" ]; then
  echo "📝 Initializing environment variable template at backend/.env..."
  cat <<EOT > backend/.env
# ===========================================================================
#  SOLANA DEX PREDATOR - ENVIRONMENTAL VARIABLES (LOCAL CONFIG)
# ===========================================================================

# Network Endpoints
RPC_ENDPOINT=https://api.mainnet-beta.solana.com
HELIUS_API_KEY=your_helius_api_key_here
JUPITER_API_KEY=your_jupiter_api_key_here
ZERO_X_API_KEY=your_0x_api_key_here

# Solana Wallet Credentials (BURNER WALLET ONLY)
SOLANA_PRIVATE_KEY=your_burner_wallet_private_key_here

# Execution Strategy Parameters
TRADE_MARGIN_PERCENT=0.40
MAX_SLIPPAGE_PERCENT=2.0
TRAILING_STOP_LOSS_PERCENT=20.0
INITIAL_CAPITAL=12.0
EOT
  chmod 600 backend/.env
  echo "✅ Local .env template initialized with read/write permissions locked to root."
else
  echo "ℹ️  Existing backend/.env file detected. Keeping current configuration."
fi

# 7. Create systemd System Service
echo "⚙️  Configuring systemd service daemon (/etc/systemd/system/dexhelp.service)..."
cat <<EOT > /etc/systemd/system/dexhelp.service
[Unit]
Description=Solana Dex Predator Trading Daemon
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/.venv/bin/python -u backend/live_paper_trader.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=dexhelp

[Install]
WantedBy=multi-user.target
EOT

# 8. Reload systemd daemon and enable service
echo "🔄 Reloading systemd manager configuration..."
systemctl daemon-reload
systemctl enable dexhelp.service

echo "========================================================================="
echo "✅ DEPLOYMENT SETUP COMPLETE!"
echo "========================================================================="
echo "📋 Next Steps:"
echo "  1. Edit your local environment variables file to set your API keys & burner private key:"
echo "     nano $PROJECT_DIR/backend/.env"
echo "  2. Start the automated background service daemon:"
echo "     systemctl start dexhelp"
echo "  3. Monitor the live background logs in real-time:"
echo "     journalctl -u dexhelp -f -n 100"
echo "========================================================================="
