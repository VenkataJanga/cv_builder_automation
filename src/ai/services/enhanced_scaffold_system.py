"""
Enhanced Scaffold System - Next Generation
Provides comprehensive scaffolding for CV enhancement with role-specific templates
"""

from typing import Dict, List, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
import re


class ScaffoldLevel(str, Enum):
    """Scaffold complexity levels"""
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXECUTIVE = "executive"


class RoleCategory(str, Enum):
    """Role categories for targeted scaffolding"""
    SOFTWARE_ENGINEER = "software_engineer"
    DATA_SCIENTIST = "data_scientist"
    AI_ML_ENGINEER = "ai_ml_engineer"
    DEVOPS_ENGINEER = "devops_engineer"
    SOLUTION_ARCHITECT = "solution_architect"
    TECHNICAL_LEAD = "technical_lead"
    MANAGER = "manager"
    EXECUTIVE = "executive"


class EnhancementSuggestion(BaseModel):
    """Individual enhancement suggestion"""
    field: str
    category: str  # content, structure, formatting, achievements
    priority: str  # critical, high, medium, low
    suggestion: str
    example: Optional[str] = None
    impact_score: float = Field(ge=0.0, le=1.0)
    auto_applicable: bool = False
    rationale: str = ""


class ScaffoldTemplate(BaseModel):
    """Scaffold template definition"""
    template_id: str
    name: str
    role_category: RoleCategory
    level: ScaffoldLevel
    sections: Dict[str, Any]
    required_fields: List[str]
    optional_fields: List[str]
    enhancement_rules: List[Dict[str, Any]]
    quality_thresholds: Dict[str, float]


class EnhancedScaffoldSystem:
    """Next-generation scaffold system with intelligent enhancement"""
    
    def __init__(self):
        self.templates = self._initialize_templates()
        self.enhancement_rules = self._initialize_enhancement_rules()
    
    def _initialize_templates(self) -> Dict[str, ScaffoldTemplate]:
        """Initialize role-specific templates"""
        return {
            "ai_ml_engineer": ScaffoldTemplate(
                template_id="ai_ml_001",
                name="AI/ML Engineer Professional",
                role_category=RoleCategory.AI_ML_ENGINEER,
                level=ScaffoldLevel.ADVANCED,
                sections={
                    "header": {
                        "required": ["full_name", "current_title", "email", "contact_number"],
                        "optional": ["linkedin", "github", "portfolio"]
                    },
                    "summary": {
                        "min_length": 150,
                        "max_length": 300,
                        "key_elements": ["years_experience", "expertise_areas", "achievements"]
                    },
                    "technical_skills": {
                        "categories": [
                            "programming_languages",
                            "ml_frameworks",
                            "cloud_platforms",
                            "tools_platforms"
                        ],
                        "min_skills_per_category": 3
                    },
                    "experience": {
                        "min_projects": 2,
                        "project_fields": ["name", "client", "role", "technologies", "achievements"]
                    },
                    "education": {
                        "required": True,
                        "preferred_fields": ["degree", "field", "institution", "year"]
                    }
                },
                required_fields=["full_name", "email", "summary", "skills", "experience"],
                optional_fields=["certifications", "publications", "awards"],
                enhancement_rules=[
                    {
                        "rule_id": "quantify_achievements",
                        "applies_to": ["experience", "projects"],
                        "description": "Add quantifiable metrics to achievements"
                    },
                    {
                        "rule_id": "technical_depth",
                        "applies_to": ["skills", "projects"],
                        "description": "Show depth in AI/ML technologies"
                    }
                ],
                quality_thresholds={
                    "completeness": 0.85,
                    "detail_level": 0.80,
                    "achievement_impact": 0.75
                }
            ),
            "software_engineer": ScaffoldTemplate(
                template_id="swe_001",
                name="Software Engineer Professional",
                role_category=RoleCategory.SOFTWARE_ENGINEER,
                level=ScaffoldLevel.INTERMEDIATE,
                sections={
                    "header": {
                        "required": ["full_name", "current_title", "email"],
                        "optional": ["github", "portfolio"]
                    },
                    "summary": {
                        "min_length": 120,
                        "max_length": 250,
                        "key_elements": ["years_experience", "technical_stack", "problem_solving"]
                    },
                    "technical_skills": {
                        "categories": [
                            "programming_languages",
                            "frameworks",
                            "databases",
                            "tools"
                        ],
                        "min_skills_per_category": 2
                    }
                },
                required_fields=["full_name", "email", "skills", "experience"],
                optional_fields=["certifications", "open_source"],
                enhancement_rules=[
                    {
                        "rule_id": "code_impact",
                        "applies_to": ["projects"],
                        "description": "Highlight code quality and impact"
                    }
                ],
                quality_thresholds={
                    "completeness": 0.80,
                    "detail_level": 0.75
                }
            )
        }
    
    def _initialize_enhancement_rules(self) -> Dict[str, Any]:
        """Initialize enhancement rules"""
        return {
            "content_enhancement": {
                "summary": [
                    "Start with years of experience",
                    "Include key technical skills",
                    "Highlight major achievements",
                    "Mention domain expertise"
                ],
                "experience": [
                    "Use action verbs (Led, Developed, Implemented)",
                    "Quantify results (%, $, time saved)",
                    "Show technical depth",
                    "Highlight leadership and collaboration"
                ],
                "skills": [
                    "Group by category",
                    "Include proficiency levels",
                    "Show recent technologies",
                    "Balance breadth and depth"
                ]
            },
            "structure_enhancement": {
                "ordering": [
                    "Header/Contact",
                    "Professional Summary",
                    "Technical Skills",
                    "Work Experience",
                    "Projects",
                    "Education",
                    "Certifications",
                    "Additional"
                ],
                "formatting": [
                    "Consistent date formats",
                    "Clear section headers",
                    "Bullet points for lists",
                    "Proper spacing"
                ]
            },
            "achievement_enhancement": {
                "metrics": [
                    "Performance improvements (%)",
                    "Cost savings ($)",
                    "Time reduction (hours/days)",
                    "Team size (people led)",
                    "User impact (users/downloads)",
                    "Code quality (test coverage, bugs reduced)"
                ],
                "impact_verbs": [
                    "Architected", "Developed", "Led", "Implemented",
                    "Optimized", "Reduced", "Increased", "Delivered",
                    "Collaborated", "Mentored", "Designed", "Built"
                ]
            }
        }
    
    def detect_role_category(self, cv_data: Dict[str, Any]) -> RoleCategory:
        """Detect the best role category for the CV"""
        
        # Analyze title
        title = cv_data.get("header", {}).get("current_title", "").lower()
        
        # Analyze skills
        skills = cv_data.get("skills", [])
        ai_frameworks = cv_data.get("ai_frameworks", [])
        
        # Role detection logic
        if any(keyword in title for keyword in ["ai", "ml", "machine learning", "data scientist"]):
            if len(ai_frameworks) > 2:
                return RoleCategory.AI_ML_ENGINEER
            return RoleCategory.DATA_SCIENTIST
        
        if "architect" in title:
            return RoleCategory.SOLUTION_ARCHITECT
        
        if any(keyword in title for keyword in ["lead", "principal", "staff"]):
            return RoleCategory.TECHNICAL_LEAD
        
        if any(keyword in title for keyword in ["devops", "sre", "infrastructure"]):
            return RoleCategory.DEVOPS_ENGINEER
        
        if any(keyword in title for keyword in ["manager", "director", "vp", "head"]):
            return RoleCategory.MANAGER
        
        # Default to software engineer
        return RoleCategory.SOFTWARE_ENGINEER
    
    def detect_level(self, cv_data: Dict[str, Any]) -> ScaffoldLevel:
        """Detect the appropriate scaffold level"""
        
        # Analyze experience
        experience_years = self._extract_years_experience(cv_data)
        
        # Analyze leadership indicators
        leadership_indicators = self._count_leadership_indicators(cv_data)
        
        # Analyze complexity
        tech_breadth = len(cv_data.get("skills", [])) + len(cv_data.get("secondary_skills", []))
        
        # Level detection logic
        if experience_years >= 10 and leadership_indicators >= 3:
            return ScaffoldLevel.EXECUTIVE
        elif experience_years >= 7 or leadership_indicators >= 2:
            return ScaffoldLevel.ADVANCED
        elif experience_years >= 3:
            return ScaffoldLevel.INTERMEDIATE
        else:
            return ScaffoldLevel.BASIC
    
    def _extract_years_experience(self, cv_data: Dict[str, Any]) -> int:
        """Extract total years of experience"""
        exp_str = cv_data.get("header", {}).get("total_experience", "0")
        match = re.search(r'(\d+)', exp_str)
        return int(match.group(1)) if match else 0
    
    def _count_leadership_indicators(self, cv_data: Dict[str, Any]) -> int:
        """Count leadership indicators in CV"""
        count = 0
        
        # Check title
        title = cv_data.get("header", {}).get("current_title", "").lower()
        if any(word in title for word in ["lead", "senior", "principal", "architect", "manager"]):
            count += 1
        
        # Check leadership section
        if cv_data.get("leadership", {}):
            count += 1
        
        # Check experience for leadership keywords
        experiences = cv_data.get("work_experience", []) + cv_data.get("project_experience", [])
        for exp in experiences:
            desc = str(exp.get("description", "")).lower()
            resp = str(exp.get("responsibilities", "")).lower()
            if any(word in desc + resp for word in ["led", "managed", "mentored", "coordinated"]):
                count += 1
                break
        
        return count
    
    def generate_enhancement_suggestions(
        self,
        cv_data: Dict[str, Any],
        role_category: Optional[RoleCategory] = None,
        level: Optional[ScaffoldLevel] = None
    ) -> List[EnhancementSuggestion]:
        """Generate comprehensive enhancement suggestions"""
        
        # Auto-detect if not provided
        if not role_category:
            role_category = self.detect_role_category(cv_data)
        if not level:
            level = self.detect_level(cv_data)
        
        suggestions = []
        
        # Get appropriate template
        template_key = f"{role_category.value}"
        template = self.templates.get(template_key)
        
        if not template:
            template = self.templates.get("software_engineer")
        
        # Check completeness
        suggestions.extend(self._check_completeness(cv_data, template))
        
        # Check content quality
        suggestions.extend(self._check_content_quality(cv_data, template))
        
        # Check achievements
        suggestions.extend(self._check_achievements(cv_data))
        
        # Check structure
        suggestions.extend(self._check_structure(cv_data, template))
        
        # Sort by priority and impact
        suggestions.sort(key=lambda x: (
            self._priority_score(x.priority),
            -x.impact_score
        ))
        
        return suggestions
    
    def _check_completeness(
        self,
        cv_data: Dict[str, Any],
        template: ScaffoldTemplate
    ) -> List[EnhancementSuggestion]:
        """Check for missing required fields"""
        suggestions = []
        
        for field in template.required_fields:
            if field not in cv_data or not cv_data[field]:
                suggestions.append(EnhancementSuggestion(
                    field=field,
                    category="completeness",
                    priority="critical",
                    suggestion=f"Add {field.replace('_', ' ')} to complete your CV",
                    impact_score=0.9,
                    rationale=f"{field} is a required field for this role"
                ))
        
        return suggestions
    
    def _check_content_quality(
        self,
        cv_data: Dict[str, Any],
        template: ScaffoldTemplate
    ) -> List[EnhancementSuggestion]:
        """Check content quality"""
        suggestions = []
        
        # Check summary length
        summary = cv_data.get("summary", "")
        if summary:
            min_len = template.sections.get("summary", {}).get("min_length", 100)
            if len(summary) < min_len:
                suggestions.append(EnhancementSuggestion(
                    field="summary",
                    category="content",
                    priority="high",
                    suggestion=f"Expand professional summary (current: {len(summary)} chars, recommended: {min_len}+)",
                    example="Include years of experience, key skills, and major achievements",
                    impact_score=0.8,
                    rationale="A comprehensive summary improves readability and impact"
                ))
        
        # Check skills categorization
        if "skills" in cv_data:
            if not isinstance(cv_data["skills"], dict):
                suggestions.append(EnhancementSuggestion(
                    field="skills",
                    category="structure",
                    priority="medium",
                    suggestion="Organize skills into categories (Languages, Frameworks, Tools, etc.)",
                    impact_score=0.7,
                    rationale="Categorized skills are easier to scan and more professional"
                ))
        
        return suggestions
    
    def _check_achievements(self, cv_data: Dict[str, Any]) -> List[EnhancementSuggestion]:
        """Check for quantifiable achievements"""
        suggestions = []
        
        experiences = cv_data.get("work_experience", []) + cv_data.get("project_experience", [])
        
        achievement_count = 0
        quantified_count = 0
        
        for exp in experiences:
            desc = str(exp.get("description", "")) + " " + str(exp.get("responsibilities", ""))
            
            # Check for achievements
            if any(word in desc.lower() for word in ["achieved", "improved", "increased", "reduced", "delivered"]):
                achievement_count += 1
            
            # Check for quantified achievements
            if re.search(r'\d+\s*%|\$\d+|\d+\s*(hours|days|users|x)', desc):
                quantified_count += 1
        
        # Suggest adding quantifiable achievements if lacking
        if achievement_count < len(experiences):
            suggestions.append(EnhancementSuggestion(
                field="experience",
                category="achievements",
                priority="high",
                suggestion="Add measurable achievements to your experience descriptions",
                example="'Improved system performance by 40%' or 'Led team of 5 developers'",
                impact_score=0.85,
                rationale="Quantifiable achievements demonstrate concrete impact"
            ))
        
        return suggestions
    
    def _check_structure(
        self,
        cv_data: Dict[str, Any],
        template: ScaffoldTemplate
    ) -> List[EnhancementSuggestion]:
        """Check CV structure"""
        suggestions = []
        
        # Check section ordering
        expected_order = self.enhancement_rules["structure_enhancement"]["ordering"]
        
        # Check for proper organization
        if not cv_data.get("header"):
            suggestions.append(EnhancementSuggestion(
                field="header",
                category="structure",
                priority="critical",
                suggestion="Add a proper header section with contact information",
                impact_score=0.95,
                rationale="Header is the first thing recruiters see"
            ))
        
        return suggestions
    
    def _priority_score(self, priority: str) -> int:
        """Convert priority to numeric score for sorting"""
        return {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3
        }.get(priority, 4)
    
    def apply_scaffold(
        self,
        cv_data: Dict[str, Any],
        scaffold_id: str
    ) -> Dict[str, Any]:
        """Apply a scaffold template to CV data"""
        
        # Find template
        template = None
        for t in self.templates.values():
            if t.template_id == scaffold_id:
                template = t
                break
        
        if not template:
            return cv_data
        
        # Apply template structure
        enhanced_data = cv_data.copy()
        
        # Ensure all required sections exist
        for section_name in template.sections.keys():
            if section_name not in enhanced_data:
                enhanced_data[section_name] = {}
        
        # Apply quality standards
        enhanced_data["_metadata"] = {
            "scaffold_applied": scaffold_id,
            "template_name": template.name,
            "applied_at": datetime.utcnow().isoformat(),
            "quality_thresholds": template.quality_thresholds
        }
        
        return enhanced_data
    
    def get_template_by_role(self, role_category: RoleCategory) -> Optional[ScaffoldTemplate]:
        """Get template for a specific role"""
        return self.templates.get(role_category.value)
    
    def get_all_templates(self) -> List[ScaffoldTemplate]:
        """Get all available templates"""
        return list(self.templates.values())
