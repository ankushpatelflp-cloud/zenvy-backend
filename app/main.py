from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from app.downloader import extract_video, download_video, cleanup_temp_file
import logging
import gc
import asyncio
from contextlib import asynccontextmanager
from threading import Semaphore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Limit concurrent downloads to 2 (to prevent RAM overload on free tier)
download_semaphore = Semaphore(2)

# Startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Backend starting...")
    yield
    logger.info("Backend shutting down...")
    gc.collect()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    url: str
    format_id: str = "best"

@app.post("/extract")
async def extract(data: VideoRequest):
    """Extract video metadata without downloading"""
    try:
        result = extract_video(data.url)
        return result
    except Exception as e:
        logger.error(f"Extract error: {str(e)}")
        return {"success": False, "error": str(e)}

@app.post("/download")
async def download(data: VideoRequest, request: Request):
    """Download video with streaming response"""
    temp_file = None
    
    try:
        # Check if client disconnected
        if await request.is_disconnected():
            logger.info("Client disconnected before download")
            return JSONResponse({"success": False, "error": "Client disconnected"})
        
        # Limit concurrent downloads
        if not download_semaphore.acquire(blocking=False):
            logger.warning("Max concurrent downloads reached")
            return JSONResponse(
                {"success": False, "error": "Server busy, too many downloads"},
                status_code=429
            )
        
        try:
            logger.info(f"Download request for: {data.url}")
            
            # Download file with timeout
            temp_file, error = await asyncio.wait_for(
                asyncio.to_thread(download_video, data.url, data.format_id),
                timeout=300
            )
            
            if error or not temp_file:
                logger.error(f"Download failed: {error}")
                return JSONResponse(
                    {"success": False, "error": error},
                    status_code=400
                )
            
            logger.info(f"Starting stream response for: {temp_file}")
            
            # Create streaming response that cleans up after sending
            async def stream_and_cleanup():
                try:
                    with open(temp_file, "rb") as f:
                        chunk_size = 256 * 1024  # 256KB chunks to prevent RAM overload
                        while True:
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            yield chunk
                finally:
                    # Cleanup after streaming
                    cleanup_temp_file(temp_file)
                    gc.collect()
            
            return StreamingResponse(
                stream_and_cleanup(),
                media_type="video/mp4",
                headers={
                    "Content-Disposition": "attachment; filename=video.mp4",
                    "Cache-Control": "no-cache"
                }
            )
        
        finally:
            download_semaphore.release()
    
    except asyncio.TimeoutError:
        logger.error("Download timeout")
        if temp_file:
            cleanup_temp_file(temp_file)
        return JSONResponse(
            {"success": False, "error": "Download timeout (exceeded 5 minutes)"},
            status_code=408
        )
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        if temp_file:
            cleanup_temp_file(temp_file)
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )
    finally:
        gc.collect()

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}