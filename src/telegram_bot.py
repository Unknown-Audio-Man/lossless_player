import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext

from config import TELEGRAM_BOT_TOKEN, ALLOWED_TELEGRAM_USERS
from music_library import MusicLibrary
from player import Player

logger = logging.getLogger(__name__)

class TelegramController:
    """Telegram bot for controlling the audio player"""
    
    def __init__(self, music_library, player):
        self.music_library = music_library
        self.player = player
        self.app = None
        
        # Set player status callback
        self.player.set_status_callback(self.on_player_status_update)
    
    async def start(self):
        """Start the Telegram bot"""
        if not TELEGRAM_BOT_TOKEN:
            logger.error("Telegram bot token not configured!")
            return False
            
        try:
            self.app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
            
            # Register command handlers
            self.app.add_handler(CommandHandler("start", self.cmd_start))
            self.app.add_handler(CommandHandler("help", self.cmd_help))
            self.app.add_handler(CommandHandler("play", self.cmd_play))
            self.app.add_handler(CommandHandler("pause", self.cmd_pause))
            self.app.add_handler(CommandHandler("stop", self.cmd_stop))
            self.app.add_handler(CommandHandler("next", self.cmd_next))
            self.app.add_handler(CommandHandler("prev", self.cmd_prev))
            self.app.add_handler(CommandHandler("volume", self.cmd_volume))
            self.app.add_handler(CommandHandler("status", self.cmd_status))
            self.app.add_handler(CommandHandler("random", self.cmd_random))
            self.app.add_handler(CommandHandler("rescan", self.cmd_rescan))
            
            # Register general message handler for album searches
            self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.on_message))
            
            # Start the bot
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling()
            
            logger.info("Telegram bot started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {e}")
            return False
    
    async def stop(self):
        """Stop the Telegram bot"""
        if self.app:
            await self.app.stop()
            await self.app.shutdown()
            logger.info("Telegram bot stopped")
    
    def _is_authorized(self, user_id):
        """Check if user is authorized to control the player"""
        return len(ALLOWED_TELEGRAM_USERS) == 0 or user_id in ALLOWED_TELEGRAM_USERS
    
    async def cmd_start(self, update: Update, context: CallbackContext):
        """Handle /start command"""
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return
            
        await update.message.reply_text(
            f"👋 Hello {update.effective_user.first_name}!\n\n"
            "I'm your Raspberry Pi Lossless Audio Player controller.\n"
            "Use /help to see available commands."
        )
    
    async def cmd_help(self, update: Update, context: CallbackContext):
        """Handle /help command"""
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return
            
        help_text = (
            "🎵 *Lossless Player Commands* 🎵\n\n"
            "*Playback Controls*\n"
            "/play - Start/resume playback\n"
            "/pause - Pause playback\n"
            "/stop - Stop playback\n"
            "/next - Skip to next track\n"
            "/prev - Go to previous track\n"
            "/volume [0-100] - Set or show volume\n"
            "/status - Show current playback status\n\n"
            "*Library*\n"
            "/random - Play random album\n"
            "/rescan - Rescan music library\n\n"
            "*Search*\n"
            "Simply type album or artist name to search"
        )
        await update.message.reply_text(help_text, parse_mode="Markdown")
    
    async def cmd_play(self, update: Update, context: CallbackContext):
        """Handle /play command"""
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return
            
        if self.player.play():
            status = self.player.get_status()
            if status['album']:
                await update.message.reply_text(f"▶️ Playing: {status['album']['name']} by {status['album']['artist']}")
            else:
                await update.message.reply_text("▶️ Playback started")
        else:
            await update.message.reply_text("No album loaded. Search for an album first.")
    
    async def cmd_pause(self, update: Update, context: CallbackContext):
        """Handle /pause command"""
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return
            
        if self.player.pause():
            await update.message.reply_text("⏸️ Playback paused")
        else:
            await update.message.reply_text("Nothing is playing")
    
    async def cmd_stop(self, update: Update, context: CallbackContext):
        """Handle /stop command"""
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return
            
        self.player.stop()
        await update.message.reply_text("⏹️ Playback stopped")
    
    async def cmd_next(self, update: Update, context: CallbackContext):
        """Handle /next command"""
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return
            
        if self.player.next_track():
            status = self.player.get_status()
            if 'track' in status:
                await update.message.reply_text(f"⏭️ Now playing: {status['track']['title']}")
            else:
                await update.message.reply_text("⏭️ Skipped to next track")
        else:
            await update.message.reply_text("No playlist active or only one track available")
    
    async def cmd_prev(self, update: Update, context: CallbackContext):
        """Handle /prev command"""
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return
            
        if self.player.previous_track():
            status = self.player.get_status()
            if 'track' in status:
                await update.message.reply_text(f"⏮️ Now playing: {status['track']['title']}")
            else:
                await update.message.reply_text("⏮️ Returned to previous track")
        else:
            await update.message.reply_text("No playlist active or only one track available")
    
    async def cmd_volume(self, update: Update, context: CallbackContext):
        """Handle /volume command"""
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return
            
        if context.args and context.args[0].isdigit():
            volume = int(context.args[0])
            self.player.set_volume(volume)
            await update.message.reply_text(f"🔊 Volume set to {volume}%")
        else:
            current_vol = self.player.get_volume()
            await update.message.reply_text(f"🔊 Current volume: {current_vol}%\nUse /volume [0-100] to change.")
    
    async def cmd_status(self, update: Update, context: CallbackContext):
        """Handle /status command"""
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return
            
        status = self.player.get_status()
        
        if status['state'] == 'STOPPED':
            await update.message.reply_text("⏹️ Player is stopped")
            return
            
        if not status['album']:
            await update.message.reply_text("No album loaded")
            return
            
        status_text = f"*Currently {status['state'].lower()}*\n"
        status_text += f"🎵 *Album:* {status['album']['name']}\n"
        status_text += f"👤 *Artist:* {status['album']['artist']}\n"
        
        if 'track' in status:
            status_text += f"🎧 *Track:* {status['track']['title']}\n"
            if 'track_index' in status:
                status_text += f"📊 *Progress:* Track {status['track_index']}\n"
                
        status_text += f"🔊 *Volume:* {status['volume']}%"
        
        await update.message.reply_text(status_text, parse_mode="Markdown")
    
    async def cmd_random(self, update: Update, context: CallbackContext):
        """Handle /random command"""
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return
            
        await update.message.reply_text("🎲 Selecting a random album...")
        
        random_album = self.music_library.get_random_album()
        if not random_album:
            await update.message.reply_text("Failed to find a random album. Is the library indexed?")
            return
            
        album_tracks = self.music_library.get_album_tracks(random_album['key'])
        if not album_tracks:
            await update.message.reply_text(f"Found album '{random_album['name']}' but couldn't load its tracks.")
            return
            
        if self.player.load_playlist(random_album, album_tracks):
            self.player.play()
            await update.message.reply_text(
                f"🎲 Now playing random album:\n"
                f"*{random_album['name']}* by *{random_album['artist']}*\n"
                f"({len(album_tracks)} tracks)",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("Failed to load random album.")
    
    async def cmd_rescan(self, update: Update, context: CallbackContext):
        """Handle /rescan command"""
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return
            
        await update.message.reply_text("🔍 Rescanning music library... This may take a while.")
        
        # Run the scan in a separate thread to not block the bot
        def scan_library():
            self.music_library.index_library(force=True)
            
        # Run in thread pool
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, scan_library)
        
        album_count = len(self.music_library.albums)
        await update.message.reply_text(f"✅ Library scan complete! Found {album_count} albums.")
    
    async def on_message(self, update: Update, context: CallbackContext):
        """Handle text messages for searching albums"""
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("You are not authorized to use this bot.")
            return
            
        query = update.message.text.strip()
        if not query:
            return
            
        await update.message.reply_text(f"🔍 Searching for: {query}")
        
        # Search for albums
        results = self.music_library.search_album(query)
        
        if not results:
            await update.message.reply_text(f"No albums found matching '{query}'")
            return
            
        if len(results) == 1:
            # Only one album found, load and play it
            album = results[0]
            await update.message.reply_text(
                f"Found album: *{album['name']}* by *{album['artist']}*\n"
                f"Loading and playing now...",
                parse_mode="Markdown"
            )
            
            album_tracks = self.music_library.get_album_tracks(album['key'])
            if not album_tracks:
                await update.message.reply_text("Error: Could not load album tracks.")
                return
                
            if self.player.load_playlist(album, album_tracks):
                self.player.play()
                track_list = "\n".join([f"{i+1}. {track['title']}" for i, track in enumerate(album_tracks[:5])])
                if len(album_tracks) > 5:
                    track_list += f"\n... and {len(album_tracks) - 5} more tracks"
                    
                await update.message.reply_text(
                    f"▶️ Now playing:\n"
                    f"*{album['name']}* by *{album['artist']}*\n\n"
                    f"{track_list}",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text("Failed to load album.")
        else:
            # Multiple albums found, show options
            response = f"Found {len(results)} albums matching '{query}':\n\n"
            
            for i, album in enumerate(results[:5], 1):
                response += f"{i}. *{album['name']}* by *{album['artist']}*\n"
                
            if len(results) > 5:
                response += f"\n... and {len(results) - 5} more albums\n"
                
            response += "\nSend a more specific query to play an album."
            
            await update.message.reply_text(response, parse_mode="Markdown")
    
    async def on_player_status_update(self, status):
        """Handle player status updates"""
        # This could be used to send periodic updates to users who are subscribed
        # For now, we'll just log the status changes
        pass