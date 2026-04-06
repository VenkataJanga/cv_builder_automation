"""
Enhanced CV Enhancement Agent with stronger scaffolding capabilities.
Provides multi-level enhancement, tone adjustment, and role-specific optimization.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class EnhancementLevel(Enum):
    """Enhancement intensity levels"""
    MINIMAL = "minimal"  # Light touch, preserve original
    MODERATE = "moderate"  # Standard enhancement
    AGGRESSIVE = "aggressive"  # Maximum impact optimization


class ToneProfile(Enum):
    """Professional tone profiles"""
    TECHNICAL = "technical"  # Technical depth, precision
    LEADERSHIP = "leadership"  # Strategic, visionary
    COLLABORATIVE = "collaborative"  # Team-focused, diplomatic
    RESULTS_DRIVEN = "results_driven"  # Metrics, outcomes


@dataclass
class EnhancementConfig:
    """Configuration for enhancement operations"""
    level: EnhancementLevel = EnhancementLevel.MODERATE
    tone: ToneProfile = ToneProfile.RESULTS_DRIVEN
    preserve_metrics: bool = True
    add_power_words: bool = True
    max_length: Optional[int] = None
    target_role: Optional[str] = None


@dataclass
class EnhancementResult:
    """Result of enhancement operation with metadata"""
    original: str
    enhanced: str
    confidence: float  # 0.0 to 1.0
    changes_made: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]


class EnhancementScaffold:
    """Scaffold for structured enhancement operations"""
    
    # Power words by category
    POWER_WORDS = {
        "leadership": [
            "spearheaded", "orchestrated", "championed", "pioneered",
            "steered", "transformed", "architected", "directed"
        ],
        "technical": [
            "engineered", "architected", "designed", "implemented",
            "optimized", "automated", "integrated", "developed"
        ],
        "results": [
            "achieved", "delivered", "accelerated", "improved",
            "increased", "reduced", "enhanced", "streamlined"
        ],
        "collaboration": [
            "collaborated", "facilitated", "coordinated", "aligned",
            "partnered", "mentored", "guided", "unified"
        ]
    }
    
    # Weak words to replace
    WEAK_WORDS = {
        "did": "executed",
        "made": "created",
        "worked on": "developed",
        "helped": "facilitated",
        "was responsible for": "led",
        "involved in": "contributed to",
        "handled": "managed",
        "dealt with": "resolved"
    }
    
    # Metric patterns to preserve
    METRIC_PATTERNS = [
        r'\d+%',  # Percentages
        r'\$\d+[KMB]?',  # Dollar amounts
        r'\d+[x×]',  # Multipliers
        r'\d+\s*(?:hours?|days?|weeks?|months?)',  # Time
        r'\d+\s*(?:users?|customers?|clients?)',  # Scale
    ]
    
    def __init__(self, config: Optional[EnhancementConfig] = None):
        self.config = config or EnhancementConfig()
    
    def enhance_text(self, text: str, context: Optional[Dict[str, Any]] = None) -> EnhancementResult:
        """
        Enhance text with full tracking and confidence scoring
        
        Args:
            text: Original text to enhance
            context: Additional context (role, section, etc.)
        
        Returns:
            EnhancementResult with enhanced text and metadata
        """
        if not text or not text.strip():
            return EnhancementResult(
                original=text,
                enhanced=text,
                confidence=1.0,
                changes_made=[],
                warnings=["Empty or whitespace-only text"],
                metadata={"skipped": True}
            )
        
        original = text.strip()
        enhanced = original
        changes = []
        warnings = []
        
        # Extract and preserve metrics
        metrics = self._extract_metrics(enhanced)
        if metrics:
            changes.append(f"Preserved {len(metrics)} metrics")
        
        # Replace weak words
        enhanced, weak_replacements = self._replace_weak_words(enhanced)
        if weak_replacements:
            changes.extend([f"Replaced '{w[0]}' with '{w[1]}'" for w in weak_replacements[:3]])
        
        # Add power words if not present
        if self.config.add_power_words:
            enhanced, power_added = self._add_power_words(enhanced, context)
            if power_added:
                changes.append(f"Added {len(power_added)} power words")
        
        # Apply tone profile
        enhanced = self._apply_tone(enhanced, self.config.tone)
        
        # Role-specific optimization
        if self.config.target_role:
            enhanced = self._optimize_for_role(enhanced, self.config.target_role)
            changes.append(f"Optimized for {self.config.target_role}")
        
        # Length constraint
        if self.config.max_length and len(enhanced) > self.config.max_length:
            enhanced = self._truncate_smart(enhanced, self.config.max_length)
            warnings.append(f"Truncated to {self.config.max_length} characters")
        
        # Calculate confidence
        confidence = self._calculate_confidence(original, enhanced, changes, warnings)
        
        return EnhancementResult(
            original=original,
            enhanced=enhanced,
            confidence=confidence,
            changes_made=changes,
            warnings=warnings,
            metadata={
                "metrics_found": len(metrics),
                "weak_words_replaced": len(weak_replacements),
                "length_original": len(original),
                "length_enhanced": len(enhanced),
                "tone": self.config.tone.value,
                "level": self.config.level.value
            }
        )
    
    def _extract_metrics(self, text: str) -> List[str]:
        """Extract quantitative metrics from text"""
        import re
        metrics = []
        for pattern in self.METRIC_PATTERNS:
            metrics.extend(re.findall(pattern, text))
        return metrics
    
    def _replace_weak_words(self, text: str) -> Tuple[str, List[Tuple[str, str]]]:
        """Replace weak words with stronger alternatives"""
        replacements = []
        result = text
        
        for weak, strong in self.WEAK_WORDS.items():
            if weak.lower() in result.lower():
                # Case-insensitive replacement
                import re
                pattern = re.compile(re.escape(weak), re.IGNORECASE)
                if pattern.search(result):
                    result = pattern.sub(strong, result, count=1)
                    replacements.append((weak, strong))
        
        return result, replacements
    
    def _add_power_words(self, text: str, context: Optional[Dict[str, Any]]) -> Tuple[str, List[str]]:
        """Add power words based on context"""
        added = []
        
        # Determine which power word category to use
        if context and context.get("section") == "leadership":
            category = "leadership"
        elif context and "technical" in context.get("section", "").lower():
            category = "technical"
        else:
            category = "results"
        
        # Check if text already has strong verbs
        has_power_word = any(
            word in text.lower() 
            for words in self.POWER_WORDS.values() 
            for word in words
        )
        
        if not has_power_word and not text[0].isupper():
            # Add appropriate power word at start
            power_word = self.POWER_WORDS[category][0]
            text = f"{power_word.capitalize()} {text}"
            added.append(power_word)
        
        return text, added
    
    def _apply_tone(self, text: str, tone: ToneProfile) -> str:
        """Apply tone-specific adjustments"""
        if tone == ToneProfile.TECHNICAL:
            # Ensure technical precision
            if "system" in text.lower() and "architecture" not in text.lower():
                text = text.replace("system", "system architecture")
        
        elif tone == ToneProfile.LEADERSHIP:
            # Add strategic framing
            if not any(word in text.lower() for word in ["strategic", "vision", "transformation"]):
                if "led" in text.lower():
                    text = text.replace("led", "strategically led")
        
        elif tone == ToneProfile.RESULTS_DRIVEN:
            # Emphasize outcomes
            if "implemented" in text.lower() and "resulting in" not in text.lower():
                text += " with measurable business impact"
        
        return text
    
    def _optimize_for_role(self, text: str, role: str) -> str:
        """Optimize text for specific role"""
        role_keywords = {
            "technical_manager": ["technical leadership", "architecture", "engineering excellence"],
            "project_manager": ["delivery", "stakeholder", "project execution"],
            "architect": ["design", "architecture", "scalability", "patterns"],
            "developer": ["implementation", "code quality", "technical excellence"]
        }
        
        keywords = role_keywords.get(role, [])
        # Add role context if appropriate
        if keywords and not any(kw in text.lower() for kw in keywords):
            text += f" demonstrating {keywords[0]}"
        
        return text
    
    def _truncate_smart(self, text: str, max_length: int) -> str:
        """Truncate while preserving sentence structure"""
        if len(text) <= max_length:
            return text
        
        # Try to truncate at sentence boundary
        truncated = text[:max_length]
        last_period = truncated.rfind('.')
        
        if last_period > max_length * 0.7:  # If we can keep 70% of text
            return truncated[:last_period + 1]
        
        # Otherwise truncate at word boundary
        last_space = truncated.rfind(' ')
        if last_space > 0:
            return truncated[:last_space] + "..."
        
        return truncated + "..."
    
    def _calculate_confidence(
        self, 
        original: str, 
        enhanced: str, 
        changes: List[str], 
        warnings: List[str]
    ) -> float:
        """Calculate confidence score for enhancement"""
        confidence = 1.0
        
        # Reduce confidence for warnings
        confidence -= len(warnings) * 0.1
        
        # Reduce confidence if changes are minimal
        if len(changes) < 2:
            confidence -= 0.2
        
        # Reduce confidence if text changed dramatically
        if len(enhanced) > len(original) * 1.5:
            confidence -= 0.15
        
        # Increase confidence if metrics preserved
        if "metrics" in str(changes).lower():
            confidence += 0.1
        
        return max(0.0, min(1.0, confidence))


class EnhancementAgentV2:
    """Enhanced CV Enhancement Agent with scaffolding"""
    
    def __init__(self):
        self.scaffold = EnhancementScaffold()
    
    def enhance_summary(
        self, 
        text: str, 
        role: Optional[str] = None,
        config: Optional[EnhancementConfig] = None
    ) -> EnhancementResult:
        """Enhance professional summary with full tracking"""
        if config:
            self.scaffold.config = config
        else:
            self.scaffold.config = EnhancementConfig(
                level=EnhancementLevel.MODERATE,
                tone=ToneProfile.LEADERSHIP,
                target_role=role
            )
        
        context = {"section": "summary", "role": role}
        return self.scaffold.enhance_text(text, context)
    
    def enhance_achievement(
        self, 
        text: str,
        require_metrics: bool = True
    ) -> EnhancementResult:
        """Enhance achievement with metrics focus"""
        config = EnhancementConfig(
            level=EnhancementLevel.AGGRESSIVE,
            tone=ToneProfile.RESULTS_DRIVEN,
            preserve_metrics=True,
            add_power_words=True
        )
        self.scaffold.config = config
        
        context = {"section": "achievement", "require_metrics": require_metrics}
        result = self.scaffold.enhance_text(text, context)
        
        # Add warning if metrics expected but not found
        if require_metrics and result.metadata["metrics_found"] == 0:
            result.warnings.append("No quantitative metrics found - consider adding measurements")
            result.confidence *= 0.8
        
        return result
    
    def enhance_skills(
        self, 
        primary: List[str], 
        secondary: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Enhance and deduplicate skills with confidence"""
        primary_enhanced = []
        secondary_enhanced = []
        
        for skill in primary or []:
            if skill and skill.strip():
                result = self.scaffold.enhance_text(
                    skill.strip(), 
                    {"section": "skills", "type": "primary"}
                )
                primary_enhanced.append({
                    "skill": result.enhanced,
                    "original": result.original,
                    "confidence": result.confidence
                })
        
        for skill in secondary or []:
            if skill and skill.strip():
                result = self.scaffold.enhance_text(
                    skill.strip(),
                    {"section": "skills", "type": "secondary"}
                )
                secondary_enhanced.append({
                    "skill": result.enhanced,
                    "original": result.original,
                    "confidence": result.confidence
                })
        
        return {
            "primary_skills": [s["skill"] for s in primary_enhanced],
            "secondary_skills": [s["skill"] for s in secondary_enhanced],
            "metadata": {
                "primary_count": len(primary_enhanced),
                "secondary_count": len(secondary_enhanced),
                "avg_confidence": sum(s["confidence"] for s in primary_enhanced + secondary_enhanced) / 
                                  max(1, len(primary_enhanced) + len(secondary_enhanced))
            }
        }
    
    def batch_enhance(
        self, 
        items: List[str], 
        context: Dict[str, Any]
    ) -> List[EnhancementResult]:
        """Batch enhance multiple items"""
        return [self.scaffold.enhance_text(item, context) for item in items]
