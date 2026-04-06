"""
Enhancement Scaffold System
Provides structured templates and scaffolds for CV data enhancement
"""

from typing import Dict, List, Optional, Any, Callable
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class ScaffoldType(str, Enum):
    """Types of enhancement scaffolds"""
    PROFESSIONAL_SUMMARY = "professional_summary"
    SKILLS_ENHANCEMENT = "skills_enhancement"
    PROJECT_DESCRIPTION = "project_description"
    ACHIEVEMENT_FORMATTING = "achievement_formatting"
    ROLE_CONTEXTUALIZATION = "role_contextualization"
    TECHNICAL_DEPTH = "technical_depth"


class ScaffoldConfig(BaseModel):
    """Configuration for a scaffold"""
    name: str
    scaffold_type: ScaffoldType
    template: str
    required_fields: List[str]
    optional_fields: List[str] = Field(default_factory=list)
    enhancement_rules: Dict[str, Any] = Field(default_factory=dict)
    quality_threshold: float = 0.7
    max_iterations: int = 3


class EnhancementScaffold:
    """
    Base scaffold for enhancing CV sections with structured templates
    """
    
    def __init__(self, config: ScaffoldConfig):
        self.config = config
        self.enhancement_history: List[Dict] = []
    
    def apply(
        self,
        raw_data: Dict[str, Any],
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Apply scaffold to enhance data"""
        
        context = context or {}
        iteration = 0
        current_data = raw_data.copy()
        
        while iteration < self.config.max_iterations:
            # Validate required fields
            if not self._validate_fields(current_data):
                break
            
            # Apply enhancement
            enhanced = self._enhance(current_data, context, iteration)
            
            # Check quality
            quality_score = self._assess_quality(enhanced)
            
            self.enhancement_history.append({
                "iteration": iteration,
                "quality_score": quality_score,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            if quality_score >= self.config.quality_threshold:
                return enhanced
            
            current_data = enhanced
            iteration += 1
        
        return current_data
    
    def _validate_fields(self, data: Dict) -> bool:
        """Validate required fields are present"""
        return all(field in data for field in self.config.required_fields)
    
    def _enhance(
        self,
        data: Dict,
        context: Dict,
        iteration: int
    ) -> Dict[str, Any]:
        """Apply enhancement logic - to be overridden by subclasses"""
        raise NotImplementedError
    
    def _assess_quality(self, data: Dict) -> float:
        """Assess quality of enhanced data"""
        raise NotImplementedError


class ProfessionalSummaryScaffold(EnhancementScaffold):
    """Scaffold for enhancing professional summaries"""
    
    def _enhance(self, data: Dict, context: Dict, iteration: int) -> Dict[str, Any]:
        """Enhance professional summary with structured approach"""
        
        summary_template = """
        {experience_intro} {domain_expertise} {technical_strengths} {key_achievements} {career_focus}
        """
        
        components = {
            "experience_intro": self._build_experience_intro(data),
            "domain_expertise": self._build_domain_expertise(data),
            "technical_strengths": self._build_technical_strengths(data),
            "key_achievements": self._build_key_achievements(data),
            "career_focus": self._build_career_focus(data)
        }
        
        enhanced_summary = summary_template.format(**components).strip()
        
        data["enhanced_summary"] = enhanced_summary
        data["components"] = components
        
        return data
    
    def _build_experience_intro(self, data: Dict) -> str:
        """Build experience introduction"""
        years = data.get("total_experience", "")
        role = data.get("current_title", "")
        
        if years and role:
            return f"Accomplished {role} with {years} of progressive experience"
        elif years:
            return f"Professional with {years} of experience"
        else:
            return "Experienced professional"
    
    def _build_domain_expertise(self, data: Dict) -> str:
        """Build domain expertise statement"""
        domains = data.get("domain_expertise", [])
        if domains:
            domain_str = ", ".join(domains[:3])
            return f"in {domain_str}"
        return ""
    
    def _build_technical_strengths(self, data: Dict) -> str:
        """Build technical strengths"""
        skills = data.get("primary_skills", [])
        if skills:
            top_skills = ", ".join(skills[:4])
            return f". Expertise in {top_skills}"
        return ""
    
    def _build_key_achievements(self, data: Dict) -> str:
        """Build key achievements"""
        achievements = data.get("achievements", [])
        if achievements:
            return f". {achievements[0]}"
        return ""
    
    def _build_career_focus(self, data: Dict) -> str:
        """Build career focus"""
        target_role = data.get("target_role")
        if target_role:
            return f". Focused on advancing in {target_role} roles"
        return ""
    
    def _assess_quality(self, data: Dict) -> float:
        """Assess summary quality"""
        score = 0.0
        
        summary = data.get("enhanced_summary", "")
        
        # Length check
        if 150 <= len(summary) <= 500:
            score += 0.3
        
        # Component presence
        components = data.get("components", {})
        score += (len([c for c in components.values() if c]) / 5) * 0.4
        
        # Keyword density
        keywords = ["experience", "expertise", "skill", "professional"]
        keyword_count = sum(1 for kw in keywords if kw in summary.lower())
        score += min(keyword_count / len(keywords), 1.0) * 0.3
        
        return min(score, 1.0)


class SkillsEnhancementScaffold(EnhancementScaffold):
    """Scaffold for enhancing skills categorization and depth"""
    
    def _enhance(self, data: Dict, context: Dict, iteration: int) -> Dict[str, Any]:
        """Enhance skills with categorization and proficiency"""
        
        raw_skills = data.get("skills", [])
        
        # Categorize skills
        categorized = self._categorize_skills(raw_skills)
        
        # Add proficiency levels
        with_proficiency = self._add_proficiency_levels(categorized, context)
        
        # Group related skills
        grouped = self._group_related_skills(with_proficiency)
        
        data["enhanced_skills"] = {
            "categorized": categorized,
            "with_proficiency": with_proficiency,
            "grouped": grouped,
            "total_count": len(raw_skills)
        }
        
        return data
    
    def _categorize_skills(self, skills: List[str]) -> Dict[str, List[str]]:
        """Categorize skills by type"""
        
        categories = {
            "programming_languages": [],
            "frameworks": [],
            "tools": [],
            "platforms": [],
            "methodologies": [],
            "other": []
        }
        
        # Simple categorization logic (can be enhanced with ML)
        programming_keywords = ["python", "java", "javascript", "typescript", "c++", "go", "rust"]
        framework_keywords = ["react", "angular", "vue", "django", "flask", "spring", "express"]
        tool_keywords = ["docker", "kubernetes", "jenkins", "git", "terraform"]
        platform_keywords = ["aws", "azure", "gcp", "linux", "windows"]
        methodology_keywords = ["agile", "scrum", "devops", "ci/cd", "tdd"]
        
        for skill in skills:
            skill_lower = skill.lower()
            
            if any(kw in skill_lower for kw in programming_keywords):
                categories["programming_languages"].append(skill)
            elif any(kw in skill_lower for kw in framework_keywords):
                categories["frameworks"].append(skill)
            elif any(kw in skill_lower for kw in tool_keywords):
                categories["tools"].append(skill)
            elif any(kw in skill_lower for kw in platform_keywords):
                categories["platforms"].append(skill)
            elif any(kw in skill_lower for kw in methodology_keywords):
                categories["methodologies"].append(skill)
            else:
                categories["other"].append(skill)
        
        return {k: v for k, v in categories.items() if v}
    
    def _add_proficiency_levels(
        self,
        categorized: Dict[str, List[str]],
        context: Dict
    ) -> Dict[str, Dict[str, str]]:
        """Add proficiency levels to skills"""
        
        with_proficiency = {}
        
        # Use context clues (years of experience, project count) to infer proficiency
        experience_years = context.get("total_experience_years", 0)
        
        for category, skills in categorized.items():
            with_proficiency[category] = {}
            for skill in skills:
                # Simple heuristic (would use ML in production)
                if experience_years >= 5:
                    proficiency = "Expert"
                elif experience_years >= 3:
                    proficiency = "Advanced"
                else:
                    proficiency = "Intermediate"
                
                with_proficiency[category][skill] = proficiency
        
        return with_proficiency
    
    def _group_related_skills(
        self,
        with_proficiency: Dict[str, Dict[str, str]]
    ) -> Dict[str, List[str]]:
        """Group related skills together"""
        
        groups = {
            "Full Stack Development": [],
            "Cloud & DevOps": [],
            "Data & AI": [],
            "Architecture & Design": []
        }
        
        # Simple grouping logic
        for category, skills in with_proficiency.items():
            for skill in skills.keys():
                skill_lower = skill.lower()
                
                if any(kw in skill_lower for kw in ["react", "angular", "node", "javascript"]):
                    groups["Full Stack Development"].append(skill)
                elif any(kw in skill_lower for kw in ["aws", "azure", "docker", "kubernetes"]):
                    groups["Cloud & DevOps"].append(skill)
                elif any(kw in skill_lower for kw in ["ai", "ml", "data", "python", "tensorflow"]):
                    groups["Data & AI"].append(skill)
                elif any(kw in skill_lower for kw in ["architecture", "design", "microservices"]):
                    groups["Architecture & Design"].append(skill)
        
        return {k: v for k, v in groups.items() if v}
    
    def _assess_quality(self, data: Dict) -> float:
        """Assess skills enhancement quality"""
        score = 0.0
        
        enhanced = data.get("enhanced_skills", {})
        
        # Categorization completeness
        if enhanced.get("categorized"):
            score += 0.4
        
        # Proficiency levels added
        if enhanced.get("with_proficiency"):
            score += 0.3
        
        # Grouping done
        if enhanced.get("grouped"):
            score += 0.3
        
        return min(score, 1.0)


class ProjectDescriptionScaffold(EnhancementScaffold):
    """Scaffold for enhancing project descriptions"""
    
    def _enhance(self, data: Dict, context: Dict, iteration: int) -> Dict[str, Any]:
        """Enhance project descriptions with STAR method"""
        
        projects = data.get("projects", [])
        enhanced_projects = []
        
        for project in projects:
            enhanced = self._apply_star_method(project)
            enhanced_projects.append(enhanced)
        
        data["enhanced_projects"] = enhanced_projects
        
        return data
    
    def _apply_star_method(self, project: Dict) -> Dict[str, Any]:
        """Apply STAR method to project description"""
        
        enhanced = project.copy()
        
        # Situation
        situation = f"Project: {project.get('project_name', '')}"
        if project.get('client'):
            situation += f" for {project['client']}"
        
        # Task
        task = project.get('role', '')
        
        # Action
        actions = project.get('responsibilities', [])
        
        # Result
        result = project.get('impact', '')
        
        enhanced["star_format"] = {
            "situation": situation,
            "task": task,
            "actions": actions,
            "result": result
        }
        
        # Build enhanced description
        enhanced_desc_parts = [situation]
        if task:
            enhanced_desc_parts.append(f"Served as {task}")
        if actions:
            enhanced_desc_parts.append("Key contributions: " + "; ".join(actions[:3]))
        if result:
            enhanced_desc_parts.append(f"Result: {result}")
        
        enhanced["enhanced_description"] = ". ".join(enhanced_desc_parts)
        
        return enhanced
    
    def _assess_quality(self, data: Dict) -> float:
        """Assess project enhancement quality"""
        score = 0.0
        
        enhanced_projects = data.get("enhanced_projects", [])
        
        if not enhanced_projects:
            return 0.0
        
        # Check STAR completeness
        complete_count = sum(
            1 for p in enhanced_projects
            if all(p.get("star_format", {}).get(k) for k in ["situation", "task", "actions"])
        )
        
        score = complete_count / len(enhanced_projects)
        
        return score


class ScaffoldSystemOrchestrator:
    """Orchestrates multiple scaffolds for complete CV enhancement"""
    
    def __init__(self):
        self.scaffolds: Dict[ScaffoldType, EnhancementScaffold] = {}
        self._initialize_scaffolds()
    
    def _initialize_scaffolds(self):
        """Initialize all scaffolds"""
        
        # Professional Summary Scaffold
        summary_config = ScaffoldConfig(
            name="Professional Summary Enhancement",
            scaffold_type=ScaffoldType.PROFESSIONAL_SUMMARY,
            template="standard",
            required_fields=["total_experience"],
            optional_fields=["current_title", "domain_expertise", "primary_skills"],
            quality_threshold=0.7
        )
        self.scaffolds[ScaffoldType.PROFESSIONAL_SUMMARY] = ProfessionalSummaryScaffold(summary_config)
        
        # Skills Enhancement Scaffold
        skills_config = ScaffoldConfig(
            name="Skills Enhancement",
            scaffold_type=ScaffoldType.SKILLS_ENHANCEMENT,
            template="categorized",
            required_fields=["skills"],
            quality_threshold=0.7
        )
        self.scaffolds[ScaffoldType.SKILLS_ENHANCEMENT] = SkillsEnhancementScaffold(skills_config)
        
        # Project Description Scaffold
        project_config = ScaffoldConfig(
            name="Project Description Enhancement",
            scaffold_type=ScaffoldType.PROJECT_DESCRIPTION,
            template="star_method",
            required_fields=["projects"],
            quality_threshold=0.7
        )
        self.scaffolds[ScaffoldType.PROJECT_DESCRIPTION] = ProjectDescriptionScaffold(project_config)
    
    def enhance_cv(self, cv_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply all scaffolds to enhance complete CV"""
        
        enhanced_data = cv_data.copy()
        enhancement_metadata = {}
        
        # Apply each scaffold
        for scaffold_type, scaffold in self.scaffolds.items():
            try:
                result = scaffold.apply(enhanced_data, context=cv_data)
                enhanced_data.update(result)
                
                enhancement_metadata[scaffold_type.value] = {
                    "applied": True,
                    "history": scaffold.enhancement_history
                }
            except Exception as e:
                enhancement_metadata[scaffold_type.value] = {
                    "applied": False,
                    "error": str(e)
                }
        
        enhanced_data["_enhancement_metadata"] = enhancement_metadata
        
        return enhanced_data
    
    def apply_specific_scaffold(
        self,
        scaffold_type: ScaffoldType,
        data: Dict[str, Any],
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Apply a specific scaffold"""
        
        if scaffold_type not in self.scaffolds:
            raise ValueError(f"Unknown scaffold type: {scaffold_type}")
        
        scaffold = self.scaffolds[scaffold_type]
        return scaffold.apply(data, context)
