import yt_dlp
import tempfile
import os
import logging

logger = logging.getLogger(__name__)

# Configuration for Render free tier
MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500MB
DOWNLOAD_TIMEOUT = 300  # 5 minutes timeout
TEMP_DIR = tempfile.gettempdir()


def extract_video(url):
    """Extract video metadata only without downloading"""

    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "nocheckcertificate": True,
        "socket_timeout": DOWNLOAD_TIMEOUT,
        "format": "best[filesize<500M]/best",

        "extractor_retries": 3,
        "retries": 3,
        "fragment_retries": 3,
        "ignoreerrors": True,

        "extractor_args": {
            "youtube": {
                "player_client": ["android"]
            }
        },

        "http_headers": {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.9"
        }
    }

    try:
        logger.info(f"Extracting metadata from: {url}")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            if not info:
                return {
                    "success": False,
                    "error": "Could not fetch media"
                }

            filesize = info.get("filesize") or info.get("filesize_approx") or 0

            logger.info(f"Video size: {filesize / 1024 / 1024:.2f} MB")

            if filesize > MAX_VIDEO_SIZE:
                return {
                    "success": False,
                    "error": "Video too large for free server"
                }

            return {
                "success": True,
                "title": info.get("title"),
                "thumbnail": info.get("thumbnail"),
                "duration": info.get("duration"),
                "uploader": info.get("uploader"),
                "webpage_url": info.get("webpage_url"),
                "formats": [
                    {
                        "format_id": f.get("format_id"),
                        "ext": f.get("ext"),
                        "quality": f.get("format"),
                        "filesize": f.get("filesize") or f.get("filesize_approx")
                    }
                    for f in info.get("formats", [])
                    if f.get("vcodec") != "none"
                ]
            }

    except Exception as e:
        logger.error(f"Extract error: {str(e)}")

        return {
            "success": False,
            "error": str(e)
        }


def download_video(url, format_id="best"):
    """Download video"""

    try:
        temp_file = os.path.join(TEMP_DIR, "%(title)s.%(ext)s")

        ydl_opts = {
            "format": format_id,
            "outtmpl": temp_file,
            "quiet": True,
            "nocheckcertificate": True,

            "extractor_args": {
                "youtube": {
                    "player_client": ["android"]
                }
            },

            "http_headers": {
                "User-Agent": "Mozilla/5.0",
                "Accept-Language": "en-US,en;q=0.9"
            }
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            downloaded_file = ydl.prepare_filename(info)

            return {
                "success": True,
                "file_path": downloaded_file,
                "title": info.get("title")
            }

    except Exception as e:
        logger.error(f"Download error: {str(e)}")

        return {
            "success": False,
            "error": str(e)
        }