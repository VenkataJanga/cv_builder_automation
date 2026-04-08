import os
import httpx
import time
import logging
from openai import OpenAI
from openai import APIError, APIConnectionError, RateLimitError, InternalServerError, AuthenticationError
from src.core.config.settings import settings

logger = logging.getLogger(__name__)


class WhisperSpeechProvider:
    def __init__(self) -> None:
        # By default verify SSL. To bypass in dev, set OPENAI_VERIFY_SSL=false
        verify_ssl = settings.OPENAI_VERIFY_SSL

        if verify_ssl:
            # Secure client (verification ON)
            self.client = OpenAI(
                api_key=settings.OPENAI_API_KEY,
                timeout=httpx.Timeout(60.0, connect=10.0),
                max_retries=2
            )
        else:
            # DEVELOPMENT-ONLY: disable SSL verification (insecure, do NOT use in production)
            import warnings
            warnings.filterwarnings('ignore', message='Unverified HTTPS request')
            httpx_client = httpx.Client(
                verify=False,
                timeout=httpx.Timeout(60.0, connect=10.0)
            )
            self.client = OpenAI(
                api_key=settings.OPENAI_API_KEY,
                http_client=httpx_client,
                max_retries=2
            )

    def transcribe_file(self, file_path: str, language: str | None = None) -> str:
        """
        Transcribe audio file using OpenAI Whisper with retry logic.
        
        Args:
            file_path: Path to audio file
            language: Optional language code (e.g., 'en', 'es')
            
        Returns:
            Transcribed text
            
        Raises:
            Exception: If transcription fails after retries
        """
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Transcription attempt {attempt + 1}/{max_retries} for file: {file_path}")
                
                with open(file_path, "rb") as audio_file:
                    result = self.client.audio.transcriptions.create(
                        model=settings.WHISPER_MODEL,
                        file=audio_file,
                        language=language or "en",
                    )
                
                logger.info("Transcription successful")
                return getattr(result, "text", str(result))
                
            except InternalServerError as e:
                # 502 Bad Gateway, 500 Internal Server Error
                logger.warning(f"OpenAI server error (attempt {attempt + 1}/{max_retries}): {str(e)}")
                
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error("Max retries reached for OpenAI server error")
                    raise Exception(
                        "OpenAI Whisper API is currently unavailable (502 Bad Gateway). "
                        "This is typically a temporary issue with OpenAI's servers. "
                        "Please try again in a few minutes or check status.openai.com for service status."
                    ) from e
                    
            except RateLimitError as e:
                logger.warning(f"Rate limit error (attempt {attempt + 1}/{max_retries}): {str(e)}")
                
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    logger.info(f"Rate limited. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error("Max retries reached for rate limit error")
                    raise Exception(
                        "OpenAI API rate limit exceeded. Please wait a moment and try again."
                    ) from e
                    
            except APIConnectionError as e:
                logger.warning(f"Connection error (attempt {attempt + 1}/{max_retries}): {str(e)}")
                
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    logger.info(f"Connection failed. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error("Max retries reached for connection error")
                    raise Exception(
                        "Unable to connect to OpenAI API. Please check your network connection "
                        "and firewall settings. If using SSL verification bypass (OPENAI_VERIFY_SSL=false), "
                        "ensure your environment allows this configuration."
                    ) from e
                    
            except AuthenticationError as e:
                # Authentication error - no retry needed
                logger.error(f"OpenAI authentication error: {str(e)}")
                raise Exception(
                    "Authentication failed: Invalid or expired OpenAI API key. "
                    "Please check your OPENAI_API_KEY environment variable or .env file. "
                    "You can find your API key at https://platform.openai.com/account/api-keys"
                ) from e
                
            except APIError as e:
                # Generic API error
                logger.error(f"OpenAI API error: {str(e)}")
                raise Exception(
                    f"OpenAI API error: {str(e)}. Please check your API key and account status."
                ) from e
                
            except FileNotFoundError as e:
                logger.error(f"Audio file not found: {file_path}")
                raise Exception(f"Audio file not found: {file_path}") from e
                
            except Exception as e:
                logger.error(f"Unexpected error during transcription: {str(e)}")
                raise Exception(f"Transcription failed: {str(e)}") from e
        
        # Should never reach here due to the exception in the loop
        raise Exception("Transcription failed after all retry attempts")
