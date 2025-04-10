import vlc
import logging
import time
import threading
from enum import Enum
from pathlib import Path
from config import PLAYER_VOLUME

logger = logging.getLogger(__name__)

class PlayerState(Enum):
    STOPPED = 0
    PLAYING = 1
    PAUSED = 2

class Player:
    """VLC-based audio player with playlist management"""
    
    def __init__(self):
        # Initialize VLC instance with ALSA output - explicitly avoid PulseAudio
        self.instance = vlc.Instance('--no-video --aout=alsa --alsa-audio-device=hw:0')
        self.player = self.instance.media_player_new()
        self.media_list = self.instance.media_list_new()
        self.list_player = self.instance.media_list_player_new()
        self.list_player.set_media_player(self.player)
        self.list_player.set_media_list(self.media_list)
        
        # Set initial volume
        self.set_volume(PLAYER_VOLUME)
        
        # Player state
        self.state = PlayerState.STOPPED
        self.current_album = None
        self.current_track_index = -1
        self.current_playlist = []
        
        # Setup events
        self.events_manager = self.player.event_manager()
        self.events_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_media_end)
        
        # Playback status monitoring thread
        self.monitor_thread = None
        self.monitor_running = False
        
        # Status callback
        self.status_callback = None
    
    def set_status_callback(self, callback):
        """Set callback for player status updates"""
        self.status_callback = callback
    
    def _start_monitor(self):
        """Start the playback monitoring thread"""
        if self.monitor_thread is not None and self.monitor_thread.is_alive():
            return
            
        self.monitor_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_playback)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def _stop_monitor(self):
        """Stop the playback monitoring thread"""
        self.monitor_running = False
        if self.monitor_thread is not None:
            self.monitor_thread.join(timeout=1.0)
    
    def _monitor_playback(self):
        """Monitor playback status"""
        last_track_index = -1
        last_position = -1
        
        while self.monitor_running:
            if self.state == PlayerState.PLAYING:
                position = self.player.get_position()
                current_track = self.current_track_index
                
                # Report status if track changed or position changed significantly
                if (current_track != last_track_index or 
                        abs(position - last_position) > 0.05):
                    last_track_index = current_track
                    last_position = position
                    
                    if self.status_callback:
                        track_info = self.current_playlist[current_track] if 0 <= current_track < len(self.current_playlist) else None
                        status = {
                            'state': self.state.name,
                            'album': self.current_album,
                            'track': track_info,
                            'position': position,
                            'volume': self.get_volume()
                        }
                        self.status_callback(status)
                        
            time.sleep(1)
    
    def _on_media_end(self, event):
        """Handle media end event"""
        # Update current track index
        if self.state == PlayerState.PLAYING:
            self.current_track_index += 1
            if self.current_track_index >= len(self.current_playlist):
                self.current_track_index = 0
    
    def load_playlist(self, album_info, tracks):
        """Load a new playlist"""
        self.stop()
        
        # Clear current playlist
        self.media_list.lock()
        while self.media_list.count() > 0:
            self.media_list.remove_index(0)
        
        # Add new tracks
        for track in tracks:
            media = self.instance.media_new(track['path'])
            self.media_list.add_media(media)
        
        self.media_list.unlock()
        
        # Update state
        self.current_album = album_info
        self.current_playlist = tracks
        self.current_track_index = 0
        
        logger.info(f"Loaded playlist: {album_info['name']} by {album_info['artist']} ({len(tracks)} tracks)")
        return True
    
    def play(self):
        """Start or resume playback"""
        if not self.current_playlist:
            logger.warning("No playlist loaded")
            return False
            
        if self.state == PlayerState.PAUSED:
            self.list_player.play()
            self.state = PlayerState.PLAYING
            logger.info("Playback resumed")
        else:
            # Start from beginning
            self.list_player.play_item_at_index(self.current_track_index)
            self.state = PlayerState.PLAYING
            logger.info(f"Started playback: {self.current_album['name']}")
        
        self._start_monitor()
        return True
    
    def pause(self):
        """Pause playback"""
        if self.state == PlayerState.PLAYING:
            self.list_player.pause()
            self.state = PlayerState.PAUSED
            logger.info("Playback paused")
            return True
        return False
    
    def stop(self):
        """Stop playback"""
        self.list_player.stop()
        self.state = PlayerState.STOPPED
        logger.info("Playback stopped")
        return True
    
    def next_track(self):
        """Skip to next track"""
        if not self.current_playlist or len(self.current_playlist) <= 1:
            return False
            
        self.list_player.next()
        self.current_track_index = (self.current_track_index + 1) % len(self.current_playlist)
        logger.info(f"Skipped to next track: {self.current_track_index + 1}/{len(self.current_playlist)}")
        return True
    
    def previous_track(self):
        """Go to previous track"""
        if not self.current_playlist or len(self.current_playlist) <= 1:
            return False
            
        self.list_player.previous()
        self.current_track_index = (self.current_track_index - 1) % len(self.current_playlist)
        logger.info(f"Returned to previous track: {self.current_track_index + 1}/{len(self.current_playlist)}")
        return True
    
    def set_volume(self, volume):
        """Set playback volume (0-100)"""
        volume = max(0, min(100, volume))
        self.player.audio_set_volume(volume)
        logger.info(f"Volume set to {volume}%")
        return True
    
    def get_volume(self):
        """Get current volume"""
        return self.player.audio_get_volume()
    
    def get_status(self):
        """Get current player status"""
        status = {
            'state': self.state.name,
            'album': self.current_album,
            'volume': self.get_volume()
        }
        
        if self.state != PlayerState.STOPPED and 0 <= self.current_track_index < len(self.current_playlist):
            track = self.current_playlist[self.current_track_index]
            position = self.player.get_position() if self.state == PlayerState.PLAYING else 0
            status['track'] = track
            status['position'] = position
            status['track_index'] = f"{self.current_track_index + 1}/{len(self.current_playlist)}"
        
        return status
