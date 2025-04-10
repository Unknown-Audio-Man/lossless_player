#!/bin/bash

# Script to properly configure ALSA for IQAudio DAC+

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (use sudo)"
  exit 1
fi

echo "Setting up ALSA configuration for IQAudio DAC+"

# Create/modify asound.conf
cat > /etc/asound.conf << EOF
pcm.!default {
  type hw
  card 0
  device 0
}

ctl.!default {
  type hw
  card 0
}
EOF

# Set default mixer controls
echo "Setting default mixer levels"
amixer -c 0 sset Digital 0db
amixer -c 0 sset Analogue 0db

echo "Testing ALSA output with a simple tone"
speaker-test -t sine -f 440 -c 2 -D hw:0,0 -d 2

echo "ALSA configuration complete"
echo "To troubleshoot audio issues, try these commands:"
echo "  - aplay -l                   # List audio devices"
echo "  - speaker-test -c 2 -D hw:0  # Test audio output"
echo "  - alsamixer                  # Configure volume levels"
echo ""
echo "If you still have issues, make sure that:"
echo "  1. Your IQAudio DAC+ is properly seated on the Raspberry Pi"
echo "  2. The dtoverlay=iqaudio-dacplus is in /boot/config.txt"
echo "  3. You have rebooted after adding the overlay"
