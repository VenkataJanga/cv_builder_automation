import httpx
from openai import OpenAI
from src.core.config.settings import settings
from src.core.logging.logger import get_print_logger


print = get_print_logger(__name__)


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

    def structure_cv_transcript(self, text: str) -> str:
        """
        Transform a voice transcript into a structured CV document.

        Unlike professionalize_transcript_text() which produces free-form prose,
        this method outputs structured markdown sections that CanonicalAudioParser
        can reliably extract every CV field from.

        The output uses the exact section headers and inline labels the downstream
        parser (canonical_audio_parser._extract_markdown_projects et al.) recognises.
        """
        text = (text or "").strip()
        if not text or len(text) < 10:
            return text

        prompt = f"""You are a CV structuring expert. Transform the voice transcript below into a structured CV document.

CRITICAL: Follow this EXACT format — the downstream CV system depends on it:

**[Full Name]**
Portal ID: [Employee ID / Portal ID]
Current Role: [Job Title] at [Company Name]
Location: [City, Country]
Email: [email address]
Contact: [phone number]
Experience: [N] years

**Professional Summary**
[2-3 sentence professional summary preserving all factual details]

**Primary Skills:** skill1, skill2, skill3
**Secondary Skills:** skill1, skill2

**Project Experience**
**[First Project Name]**
**Client:** [Client Name]
**Project Description:** [What the project does / its purpose]
**Responsibilities:** [First specific responsibility.]
**Responsibilities:** [Second specific responsibility.]
**Technologies:** tech1, tech2, tech3

**Project Experience**
**[Second Project Name]**
**Client:** [Client Name]
**Project Description:** [What the project does / its purpose]
**Responsibilities:** [Responsibility.]
**Technologies:** tech1, tech2

**Education**
- [Degree], [Specialization], [Institution], [University], [Year], [Percentage or GPA]

**Certifications**
- [Certification Name], [Issuing Organization], [Year]

**Domain Expertise:** domain1, domain2, domain3

RULES:
1. Capture EVERY detail the speaker mentions — never discard information
2. Each project MUST start on its own **Project Experience** header line (repeat the header)
3. Put each responsibility on its own **Responsibilities:** line
4. Use comma-separated values for skills, technologies, and domains
5. If the speaker mentions Portal ID, Employee ID, Contact Number, GPA, CGPA, Grade, Percentage, or Percentile, you MUST preserve it explicitly in the structured output
6. For every education entry, include the score exactly as stated using Percentage or GPA in the final slot
7. Omit lines whose value was not mentioned (do NOT write N/A, Unknown, or None)
8. Fix grammar and spelling but preserve all factual content exactly
9. Project descriptions must explain WHAT the project does, not just repeat its name
10. Output ONLY the structured CV text — no commentary, no explanations

Voice Transcript:
{text}

Structured CV:"""

        try:
            response = self.client.chat.completions.create(
                model=settings.LLM_ENHANCEMENT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=3000,
            )
            structured = response.choices[0].message.content.strip()
            return structured if structured else self._basic_cleanup(text)
        except Exception as e:
            print(f"CV structuring failed: {e}. Using basic cleanup fallback.")
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
