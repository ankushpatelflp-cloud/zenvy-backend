from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from io import BytesIO
from fastapi.middleware.cors import CORSMiddleware
from app.downloader import extract_video
from app.bg_remover import remove_background

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    url: str

@app.post("/extract")
async def extract(data: VideoRequest):
    return extract_video(data.url)

@app.post("/remove-bg")
async def remove_bg(file: UploadFile = File(...)):
    image_bytes = await file.read()

    output_image = remove_background(image_bytes)

    return StreamingResponse(
        BytesIO(output_image),
        media_type="image/png"
    )