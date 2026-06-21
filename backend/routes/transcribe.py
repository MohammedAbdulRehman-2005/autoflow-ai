import os
import shutil
import logging
import time
import re
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from backend.services.whisper_service import WhisperService

logger = logging.getLogger("autoflow-fastapi.transcribe_router")

router = APIRouter()

# Max audio file upload size constraints: 25MB
MAX_FILE_SIZE = 25 * 1024 * 1024 
ALLOWED_EXTENSIONS = {".webm", ".mp3", ".wav", ".m4a", ".mp4", ".mpeg", ".mpga", ".ogg", ".oga"}

def sanitize_filename(filename: str) -> str:
    """Strip dangerous characters from filenames to avoid path injections."""
    name, ext = os.path.splitext(filename)
    sanitized_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", name)
    return sanitized_name + ext.lower()

@router.post("/transcribe")
async def transcribe_audio_endpoint(audio: UploadFile = File(...)):
    start_time = time.time()
    temp_filepath = None

    try:
        # Validate that a file is uploaded
        if not audio or not audio.filename:
            logger.warning("[Transcribe Route] ❌ No audio payload detected in request.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file or invalid upload container payload received."
            )

        filename = sanitize_filename(audio.filename)
        ext = os.path.splitext(filename)[1]

        # Validate MIME type and extensions
        if ext not in ALLOWED_EXTENSIONS and not audio.content_type.startswith("audio/"):
            logger.warning(f"[Transcribe Route] ❌ Rejected file signature: Name={filename} MIME={audio.content_type}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '{ext}'. Supported formats: .mp3, .wav, .webm, .m4a."
            )

        # Temporary download setup
        temp_dir = "/tmp"
        os.makedirs(temp_dir, exist_ok=True)
        temp_filepath = os.path.join(temp_dir, f"{int(time.time())}_{filename}")

        # Stream save file chunk-by-chunk to enforce memory limits and size checks
        file_size = 0
        with open(temp_filepath, "wb") as buffer:
            for chunk in iter(lambda: audio.file.read(1024 * 64), b""):
                file_size += len(chunk)
                if file_size > MAX_FILE_SIZE:
                    logger.error(f"[Transcribe Route] ❌ File size {file_size} exceeds permitted limit (25MB)")
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Uploaded audio file exceeds the maximum allowed limit of 25MB."
                    )
                buffer.write(chunk)

        file_size_mb = file_size / (1024 * 1024)
        logger.info(f"[Transcribe Route] 🎙️ Audio received: Name=\"{filename}\" Size={file_size_mb:.2f} MB Content-Type=\"{audio.content_type}\"")
        logger.info("[Transcribe Route] 📡 Directing sound bytes to Whisper neural speech decoders...")

        # Invoke Whisper service core
        transcript = WhisperService.transcribe_audio(temp_filepath, filename)

        end_time = time.time()
        duration = end_time - start_time
        
        logger.info(f"[Transcribe Route] ✅ Transcription finished successfully in {duration:.2f} seconds!")
        logger.debug(f"[Transcribe Route] Output transcript string: \"{transcript}\"")

        return {
            "success": True,
            "text": transcript,
            "duration": round(duration, 2)
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"[Transcribe Route] ❌ Internal failure processing audio transcription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failed: {str(e)}"
        )
    finally:
        # Guarantee audio file cleaning on both path resolution & failures
        if temp_filepath and os.path.exists(temp_filepath):
            try:
                os.remove(temp_filepath)
                logger.debug(f"[Transcribe Route] Cleaned up temporary audio payload at {temp_filepath}")
            except Exception as e:
                logger.error(f"[Transcribe Route] Cleanup error for system scratchpad at {temp_filepath}: {str(e)}")

