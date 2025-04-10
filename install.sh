#!/bin/bash

# Lossless Audio Player Installer
# For Raspberry Pi 3a+ with IQAudio DAC+

set -e  # Exit on error

# Text formatting
BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
RESET='\033[0m'

echo -e "${BOLD}${GREEN}========================================${RESET}"
echo -e "${BOLD}${GREEN}  Lossless Audio Player Installer      ${RESET}"
echo -e "${BOLD}${GREEN}  for Raspberry Pi with IQAudio DAC+   ${RESET}"
echo -e "${BOLD}${GREEN}========================================${RESET}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Please run as root (use sudo)${RESET}"
  exit 1
fi

# Get the actual username (not root)
if [ -n "$SUDO_USER" ]; then
  ACTUAL_USER="$SUDO_USER"
else
  ACTUAL_USER=$(logname)
fi

if [ "$ACTUAL_USER" = "root" ]; then
  echo -e "${RED}Cannot determine the actual user. Please run with sudo instead of as root.${RESET}"
  exit 1
fi

# Configuration variables
INSTALL_DIR="/home/jay/lossless_player"
SERVICE_NAME="lossless_player"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
MUSIC_SERVER_IP="192.168.0.3"
MUSIC_SERVER_SHARE="music"
MOUNT_POINT="/home/jay/music_server"

echo -e "\n${BOLD}Step 1: Installing system dependencies${RESET}"

# Update package lists
echo "Updating package lists..."
apt-get update

# Install required packages
echo "Installing required packages..."
apt-get install -y python3 python3-pip python3-venv cifs-utils vlc alsa-utils

echo -e "\n${BOLD}Step 2: Setting up directory structure${RESET}"
mkdir -p "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR/src"
mkdir -p "$INSTALL_DIR/logs"
mkdir -p "$INSTALL_DIR/systemd"
mkdir -p "$MOUNT_POINT"

chown -R $ACTUAL_USER:$ACTUAL_USER "$INSTALL_DIR"
chown -R $ACTUAL_USER:$ACTUAL_USER "$MOUNT_POINT"

echo -e "\n${BOLD}Step 3: Creating Python virtual environment${RESET}"
cd "$INSTALL_DIR"
sudo -u "$ACTUAL_USER" python3 -m venv venv
sudo -u "$ACTUAL_USER" "$INSTALL_DIR/venv/bin/pip" install --upgrade pip

echo -e "\n${BOLD}Step 4: Installing Python dependencies${RESET}"
sudo -u "$ACTUAL_USER" "$INSTALL_DIR/venv/bin/pip" install python-telegram-bot python-vlc requests mutagen python-dotenv smbprotocol

echo -e "\n${BOLD}Step 5: Configuring IQAudio DAC+${RESET}"
# Check if already configured
if grep -q "dtoverlay=iqaudio-dacplus" /boot/config.txt; then
  echo "IQAudio DAC+ already configured in /boot/config.txt"
else
  echo "Configuring IQAudio DAC+..."
  echo "# IQAudio DAC+ configuration" >> /boot/config.txt
  echo "dtoverlay=iqaudio-dacplus" >> /boot/config.txt
  echo "dtparam=audio=on" >> /boot/config.txt
  echo -e "${YELLOW}Note: You'll need to reboot for DAC changes to take effect${RESET}"
fi

echo -e "\n${BOLD}Step 6: Configuring Telegram bot${RESET}"
echo -e "${YELLOW}The player requires a Telegram bot to function properly.${RESET}"
echo -e "Please create a bot using Telegram's @BotFather and get the API token."
read -p "Enter your Telegram bot token: " TELEGRAM_TOKEN
read -p "Enter your Telegram user ID (optional, for restricted access): " TELEGRAM_USER_ID

# Create .env file
sudo -u "$ACTUAL_USER" tee "$INSTALL_DIR/.env" > /dev/null << EOF
# Lossless Audio Player Configuration

# Server configuration
MUSIC_SERVER_IP=$MUSIC_SERVER_IP
MUSIC_SERVER_SHARE=$MUSIC_SERVER_SHARE
MUSIC_SERVER_USERNAME=
MUSIC_SERVER_PASSWORD=

# Telegram configuration
TELEGRAM_BOT_TOKEN=$TELEGRAM_TOKEN
ALLOWED_TELEGRAM_USERS=$TELEGRAM_USER_ID

# Player configuration
PLAYER_VOLUME=70
EOF

echo -e "\n${BOLD}Step 7: Configuring music server access${RESET}"
echo -e "Enter credentials for accessing the music server at $MUSIC_SERVER_IP"
read -p "Username (leave blank if none required): " SERVER_USER
read -s -p "Password (leave blank if none required): " SERVER_PASS
echo
# Update .env file with credentials
if [ -n "$SERVER_USER" ]; then
  sed -i "s/MUSIC_SERVER_USERNAME=/MUSIC_SERVER_USERNAME=$SERVER_USER/" "$INSTALL_DIR/.env"
fi
if [ -n "$SERVER_PASS" ]; then
  sed -i "s/MUSIC_SERVER_PASSWORD=/MUSIC_SERVER_PASSWORD=$SERVER_PASS/" "$INSTALL_DIR/.env"
fi

echo -e "\n${BOLD}Step 8: Creating systemd service${RESET}"
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Lossless Audio Player
After=network.target

[Service]
User=$ACTUAL_USER
Group=$ACTUAL_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python3 $INSTALL_DIR/src/main.py
Restart=always
RestartSec=5
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=lossless_player

[Install]
WantedBy=multi-user.target
EOF

# Set permissions
chmod 644 "$SERVICE_FILE"

# Enable and start service
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl start "$SERVICE_NAME"

echo -e "\n${BOLD}${GREEN}Installation complete!${RESET}"
echo -e "\nLossless Audio Player has been installed and started."
echo -e "The service will automatically start on boot."
echo -e "\nTo view logs:"
echo -e "  ${YELLOW}sudo journalctl -u $SERVICE_NAME -f${RESET}"
echo -e "\nTo restart the service:"
echo -e "  ${YELLOW}sudo systemctl restart $SERVICE_NAME${RESET}"
echo -e "\nTo change configuration, edit:"
echo -e "  ${YELLOW}$INSTALL_DIR/.env${RESET}\n"
echo -e "${BOLD}${GREEN}Enjoy your music!${RESET}"

if grep -q "dtoverlay=iqaudio-dacplus" /boot/config.txt && ! grep -q "^#dtoverlay=iqaudio-dacplus" /boot/config.txt; then
  echo -e "\n${YELLOW}IMPORTANT: Please reboot your Raspberry Pi to activate the IQAudio DAC+${RESET}"
  read -p "Reboot now? [y/N] " -r REBOOT
  if [[ $REBOOT =~ ^[Yy]$ ]]; then
    echo "Rebooting..."
    reboot
  fi
fi