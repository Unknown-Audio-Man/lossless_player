import os
import subprocess
import logging
from pathlib import Path
from config import MUSIC_SERVER_IP, MUSIC_SERVER_SHARE, MUSIC_SERVER_USERNAME, MUSIC_SERVER_PASSWORD, MOUNT_POINT

logger = logging.getLogger(__name__)

class NetworkManager:
    """Handles network file system operations"""
    
    @staticmethod
    def ensure_mount_point():
        """Ensure the mount point directory exists"""
        MOUNT_POINT.mkdir(exist_ok=True)
    
    @staticmethod
    def is_mounted():
        """Check if the music server is already mounted"""
        try:
            result = subprocess.run(
                ['mount'], 
                capture_output=True, 
                text=True, 
                check=True
            )
            return str(MOUNT_POINT) in result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Error checking mount status: {e}")
            return False
    
    @staticmethod
    def mount_server():
        """Mount the music server using CIFS"""
        if NetworkManager.is_mounted():
            logger.info("Music server already mounted")
            return True
        
        NetworkManager.ensure_mount_point()
        
        # Create credentials file for safer mount
        credentials_file = Path('/home/jay/.smbcredentials')
        try:
            with open(credentials_file, 'w') as f:
                f.write(f"username={MUSIC_SERVER_USERNAME}\n")
                f.write(f"password={MUSIC_SERVER_PASSWORD}\n")
            
            # Set secure permissions
            os.chmod(credentials_file, 0o600)
            
            # Mount the share
            cmd = [
                'sudo', 'mount', '-t', 'cifs',
                f'//{MUSIC_SERVER_IP}/{MUSIC_SERVER_SHARE}',
                str(MOUNT_POINT),
                '-o', f'credentials={credentials_file},uid={os.getuid()},gid={os.getgid()}'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Successfully mounted music server at {MOUNT_POINT}")
                return True
            else:
                logger.error(f"Failed to mount music server: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error mounting music server: {e}")
            return False
    
    @staticmethod
    def unmount_server():
        """Unmount the music server"""
        if not NetworkManager.is_mounted():
            logger.info("Music server not mounted")
            return True
            
        try:
            cmd = ['sudo', 'umount', str(MOUNT_POINT)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Successfully unmounted {MOUNT_POINT}")
                return True
            else:
                logger.error(f"Failed to unmount server: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error unmounting server: {e}")
            return False