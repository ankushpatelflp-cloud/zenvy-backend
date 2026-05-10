import yt_dlp
import logging
import os
import tempfile
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration for Render free tier (512MB RAM)
MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500MB max video size
DOWNLOAD_TIMEOUT = 300  # 5 minutes timeout
TEMP_DIR = tempfile.gettempdir()

def extract_video(url):
    """Extract metadata only without downloading"""
    
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "nocheckcertificate": True,
        "socket_timeout": DOWNLOAD_TIMEOUT,
        "format": "best[filesize<500M]/best",
    }

    try:
        logger.info(f"Extracting metadata from: {url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            # Get file size to prevent memory overload
            filesize = info.get("filesize") or info.get("filesize_approx") or 0
            
            logger.info(f"Video size: {filesize / 1024 / 1024:.2f}MB")
            
            if filesize > MAX_VIDEO_SIZE:
                return {
                    "success": False,
                    "error": f"Video too large: {filesize / 1024 / 1024:.2f}MB (max {MAX_VIDEO_SIZE / 1024 / 1024}MB)"
                }

            return {
                "success": True,
                "title": info.get("title"),
                "thumbnail": info.get("thumbnail"),
                "duration": info.get("duration"),
                "filesize": filesize,
                "format_id": info.get("format_id")
            }

    except Exception as e:
        logger.error(f"Extraction error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


def download_video(url, format_id="best"):
    """Download video with streaming support and cleanup"""
    
    temp_file = None
    try:
        logger.info(f"Starting download from: {url}")
        
        # Create temp file
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".mp4",
            dir=TEMP_DIR
        )
        temp_filename = temp_file.name
        temp_file.close()
        
        logger.info(f"Temp file: {temp_filename}")
        
        ydl_opts = {
            "format": format_id or "best[filesize<500M]/best",
            "quiet": False,
            "no_warnings": False,
            "socket_timeout": DOWNLOAD_TIMEOUT,
            "outtmpl": temp_filename.replace(".mp4", ""),
            "restrict_filenames": True,
            "progress_hooks": [progress_hook],
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info(f"Downloading with options: {ydl_opts}")
            info = ydl.extract_info(url, download=True)
            
        # Check file exists and get size
        if os.path.exists(temp_filename):
            file_size = os.path.getsize(temp_filename)
            logger.info(f"Downloaded file size: {file_size / 1024 / 1024:.2f}MB")
            
            if file_size > MAX_VIDEO_SIZE:
                os.unlink(temp_filename)
                return None, f"Downloaded file exceeds size limit"
            
            return temp_filename, None
        else:
            return None, "Download failed: File not created"
    
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        if temp_file and os.path.exists(temp_filename):
            try:
                os.unlink(temp_filename)
            except:
                pass
        return None, str(e)


def progress_hook(d):
    """Log download progress"""
    if d['status'] == 'downloading':
        percent = d.get('_percent_str', 'N/A')
        speed = d.get('_speed_str', 'N/A')
        logger.info(f"Download progress: {percent} at {speed}")
    elif d['status'] == 'finished':
        logger.info(f"Download finished: {d.get('filename')}")


def cleanup_temp_file(filepath):
    """Safely delete temp file"""
    try:
        if filepath and os.path.exists(filepath):
            os.unlink(filepath)
            logger.info(f"Cleaned up: {filepath}")
    except Exception as e:
        logger.warning(f"Cleanup error: {str(e)}")