import os
import time
import logging
from openai import OpenAI

logger = logging.getLogger("autoflow-fastapi.whisper_service")

class WhisperService:
    @staticmethod
    def transcribe_audio(file_path: str, filename: str) -> str:
        """
        Sends local audio file to Groq or OpenAI Whisper transcription.
        Returns the transcribed text string.
        """
        start_time = time.time()
        groq_key = os.getenv("GROQ_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")

        if not groq_key and not openai_key:
            logger.error("[Whisper Service] No API keys configured (missing GROQ_API_KEY and OPENAI_API_KEY)")
            raise ValueError(
                "Whisper API credentials are not configured. Please add GROQ_API_KEY or OPENAI_API_KEY in your system environment secrets."
            )

        try:
            with open(file_path, "rb") as audio_file:
                if groq_key:
                    logger.info("[Whisper Service] ⚡ Initiating Groq Whisper v3 call...")
                    client = OpenAI(
                        api_key=groq_key,
                        base_url="https://api.groq.com/openai/v1"
                    )
                    response = client.audio.transcriptions.create(
                        file=(filename, audio_file.read()),
                        model="whisper-large-v3"
                    )
                    transcript = response.text
                else:
                    logger.info("[Whisper Service] 🌟 Initiating OpenAI Whisper standard call...")
                    client = OpenAI(api_key=openai_key)
                    response = client.audio.transcriptions.create(
                        file=(filename, audio_file.read()),
                        model="whisper-1"
                    )
                    transcript = response.text

            duration = time.time() - start_time
            logger.info(f"[Whisper Service] ✅ Transcription completed successfully in {duration:.2f} seconds!")
            return transcript

        except Exception as e:
            logger.error(f"[Whisper Service] ❌ Call failed with exception: {str(e)}")
            raise e

