#!/bin/bash

# 🚀 Metropolitan Bot Deployment Script

echo "🚀 Starting Metropolitan Bot Deployment..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run as root (use sudo)"
    exit 1
fi

# Set variables
PROJECT_DIR="/opt/metropolitan-bot"
SERVICE_USER="metropolitan"
SERVICE_NAME="metropolitan-bot"

echo "📁 Setting up project directory: $PROJECT_DIR"

# Create service user
if ! id "$SERVICE_USER" &>/dev/null; then
    echo "👤 Creating service user: $SERVICE_USER"
    useradd -r -s /bin/false -d $PROJECT_DIR $SERVICE_USER
else
    echo "✅ Service user already exists: $SERVICE_USER"
fi

# Create project directory
mkdir -p $PROJECT_DIR
chown $SERVICE_USER:$SERVICE_USER $PROJECT_DIR

echo "📦 Installing Python dependencies..."

# Install Python and pip if not present
if ! command -v python3 &> /dev/null; then
    echo "🐍 Installing Python 3..."
    apt update
    apt install -y python3 python3-pip python3-venv
fi

# Create virtual environment
echo "🔧 Setting up virtual environment..."
cd $PROJECT_DIR
python3 -m venv venv
source venv/bin/activate

# Install requirements
echo "📚 Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

echo "🔐 Setting up systemd service..."

# Copy service file
cp metropolitan-bot.service /etc/systemd/system/

# Update service file paths
sed -i "s|/path/to/your/metrpolitanbot|$PROJECT_DIR|g" /etc/systemd/system/metropolitan-bot.service
sed -i "s|your_user|$SERVICE_USER|g" /etc/systemv/system/metropolitan-bot.service

# Set proper permissions
chown $SERVICE_USER:$SERVICE_USER $PROJECT_DIR -R
chmod +x $PROJECT_DIR/attendance_bot.py

echo "🚀 Starting Metropolitan Bot service..."

# Reload systemd and start service
systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl start $SERVICE_NAME

# Check status
echo "📊 Service status:"
systemctl status $SERVICE_NAME

echo "✅ Deployment complete!"
echo ""
echo "📱 Your bot should now be running!"
echo "🔍 Check status: sudo systemctl status metropolitan-bot"
echo "📋 View logs: sudo journalctl -u metropolitan-bot -f"
echo "🔄 Restart: sudo systemctl restart metropolitan-bot"
echo "🛑 Stop: sudo systemctl stop metropolitan-bot"
