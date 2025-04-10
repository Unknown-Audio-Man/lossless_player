#!/usr/bin/env python3
import os
import sys
import logging
import asyncio
import signal
from pathlib import Path

# Add the project directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from config import logger
from network import NetworkManager
from music_library import MusicLibrary
from player import Player
from telegram_bot import TelegramController

class LosslessPlayerApp:
    """Main application class for the Lossless Player"""
    
    def __init__(self):
        self.running = False
        self.music_library = None
        self.player = None
        self.telegram_bot = None
        
    async def start(self):
        """Initialize and start all components"""
        self.running = True
        
        # Setup signal handlers
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self._signal_handler)
            
        logger.info("Starting Lossless Audio Player")
        
        # Initialize components
        try:
            # Mount music server
            if not NetworkManager.mount_server():
                logger.error("Failed to mount music server. Exiting.")
                return
            
            # Initialize music library
            self.music_library = MusicLibrary()
            logger.info("Music library initialized")
            
            # Start loading library in background
            asyncio.create_task(self._load_library())
            
            # Initialize player
            self.player = Player()
            logger.info("Audio player initialized")
            
            # Initialize Telegram controller
            self.telegram_bot = TelegramController(self.music_library, self.player)
            if not await self.telegram_bot.start():
                logger.error("Failed to start Telegram bot. Exiting.")
                return
            
            logger.info("Lossless Player started successfully")
            
            # Keep application running
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error in main application: {e}")
        finally:
            await self.stop()
    
    async def _load_library(self):
        """Load music library in background"""
        try:
            self.music_library.index_library()
        except Exception as e:
            logger.error(f"Error loading music library: {e}")
    
    async def stop(self):
        """Stop all components and clean up"""
        self.running = False
        logger.info("Stopping Lossless Player...")
        
        # Stop components in reverse order
        if self.telegram_bot:
            await self.telegram_bot.stop()
            
        if self.player:
            self.player.stop()
            
        # Unmount music server
        NetworkManager.unmount_server()
        
        logger.info("Lossless Player stopped")
    
    def _signal_handler(self, signum, frame):
        """Handle termination signals"""
        logger.info(f"Received signal {signum}. Initiating shutdown...")
        self.running = False

async def main():
    """Main entry point"""
    app = LosslessPlayerApp()
    await app.start()

if __name__ == "__main__":
    asyncio.run(main())