import httpx
from openai import OpenAI
from src.core.config.settings import settings


class EnhancementAgent:
    def __init__(self) -> None:
        """Initialize with OpenAI client for LLM-based enhancement"""
        verify_ssl = settings.OPENAI_VERIFY_SSL

        if verify_ssl:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        else:
            # DEVELOPMENT-ONLY: disable SSL verification
            import warnings
            warnings.filterwarnings('ignore', message='Unverified HTTPS request')
            httpx_client = httpx.Client(verify=False)
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY, http_client=httpx_client)

    def professionalize_transcript_text(self, text: str) -> str:
        """
        Use LLM to transform spoken transcript into professional CV-friendly text.
        
        This is the ONLY place where LLM should be used for text enhancement.
        - Cleans casual speech
        - Fixes grammar
        - Removes filler words
        - Converts to professional narrative
        """
        text = (text or "").strip()
        if not text or len(text) < 10:
            return text

        prompt = f"""Transform this voice transcript into professional CV text.

Rules:
1. Convert casual speech to professional narrative
2. Fix grammar and punctuation
3. Remove filler words (um, uh, like, you know, kind of, that's it)
4. Keep ALL factual information intact
5. Use professional terminology
6. Be concise and impactful
7. Do not add information that wasn't in the original

Examples:
- "I worked on Java and spring boot and handled some migration kind of work" 
  → "Experienced in Java and Spring Boot, contributing to migration initiatives"
  
- "My primary skill set is Python, Java, and I have worked on some cloud stuff"
  → "Primary skills include Python and Java with experience in cloud technologies"

Transcript:
{text}

Professional text (respond with ONLY the enhanced text, no explanations):"""

        try:
            response = self.client.chat.completions.create(
                model=settings.LLM_ENHANCEMENT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=settings.LLM_ENHANCEMENT_TEMPERATURE,
                max_tokens=settings.LLM_ENHANCEMENT_MAX_TOKENS
            )
            enhanced = response.choices[0].message.content.strip()
            return enhanced if enhanced else self._basic_cleanup(text)
        except Exception as e:
            # Fallback to basic cleanup if LLM fails
            print(f"LLM enhancement failed: {e}. Using fallback.")
            return self._basic_cleanup(text)

    def enhance_summary_text(self, text: str, role: str = None) -> str:
        """
        Enhance professional summary text for CV.
        Optional: Use for specific summary enhancement.
        """
        text = (text or "").strip()
        if not text or len(text) < 10:
            return text

        role_context = f" for a {role} role" if role else ""
        prompt = f"""Transform this into a compelling professional summary{role_context}.

Rules:
1. Make it impactful and concise (2-3 sentences)
2. Highlight key strengths and experience
3. Use action-oriented language
4. Keep it professional
5. Do not add false information

Text:
{text}

Professional summary:"""

        try:
            response = self.client.chat.completions.create(
                model=settings.LLM_ENHANCEMENT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=settings.LLM_ENHANCEMENT_TEMPERATURE,
                max_tokens=settings.LLM_SUMMARY_MAX_TOKENS
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Summary enhancement failed: {e}. Using original.")
            return text

    def enhance_achievement_text(self, text: str) -> str:
        """
        Enhance achievement/project description text.
        Optional: Use for specific achievement enhancement.
        """
        text = (text or "").strip()
        if not text or len(text) < 10:
            return text

        prompt = f"""Transform this achievement description into impactful professional text.

Rules:
1. Use action verbs (Led, Developed, Implemented, Optimized)
2. Quantify results if numbers are present
3. Be specific and concrete
4. Keep it concise
5. Do not add false metrics

Description:
{text}

Enhanced achievement:"""

        try:
            response = self.client.chat.completions.create(
                model=settings.LLM_ENHANCEMENT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=settings.LLM_ENHANCEMENT_TEMPERATURE,
                max_tokens=settings.LLM_ACHIEVEMENT_MAX_TOKENS
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Achievement enhancement failed: {e}. Using original.")
            return text

    def _basic_cleanup(self, text: str) -> str:
        """
        Fallback basic text cleanup when LLM is unavailable.
        Simple string replacements for common patterns.
        """
        replacements = {
            "i worked on": "Experienced in",
            "i have worked on": "Experienced in",
            "handled some": "contributed to",
            "kind of work": "initiatives",
            "that's it": "",
            "my primary skill set is": "Primary skills include",
            "my secondary skill set is": "Secondary skills include",
            "secondary skill set is": "Secondary skills include",
            "primary skill set is": "Primary skills include",
            "operating systems are": "Operating systems include",
            "databases are": "Databases include",
            "ai tools are worked on frameworks like": "AI tools and frameworks include",
            "worked on frameworks like": "Frameworks include",
        }

        enhanced = text
        for old, new in replacements.items():
            enhanced = enhanced.replace(old, new)
            enhanced = enhanced.replace(old.title(), new)

        enhanced = " ".join(enhanced.split())
        if enhanced and not enhanced.endswith("."):
            enhanced += "."
        return enhanced
