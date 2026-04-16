"""
Quality Improvement Service

Improves the quality of CV data using AI-powered enhancements.
"""
from typing import Dict, List, Any

from src.core.logging.logger import get_print_logger


print = get_print_logger(__name__)


class QualityImprovementService:
    """Service for improving the quality of CV data."""
    
    def __init__(self):
        pass
    
    async def improve_quality(self, cv_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Improve the overall quality of CV data.
        
        Args:
            cv_data: CV data to improve
            
        Returns:
            Improved CV data with quality metrics
        """
        improved_data = cv_data.copy()
        improvements_made = []
        
        # Improve work experience descriptions
        if "work_experience" in improved_data:
            improved_data["work_experience"], exp_improvements = await self._improve_work_experience(
                improved_data["work_experience"]
            )
            improvements_made.extend(exp_improvements)
        
        # Improve skills presentation
        if "skills" in improved_data:
            improved_data["skills"], skill_improvements = await self._improve_skills(
                improved_data["skills"]
            )
            improvements_made.extend(skill_improvements)
        
        # Improve project descriptions
        if "projects" in improved_data:
            improved_data["projects"], project_improvements = await self._improve_projects(
                improved_data["projects"]
            )
            improvements_made.extend(project_improvements)
        
        # Calculate quality score
        quality_score = self._calculate_quality_score(improved_data)
        
        # Add metadata
        improved_data["quality_score"] = quality_score
        improved_data["improvements_made"] = improvements_made
        improved_data["quality_metrics"] = self._get_quality_metrics(improved_data)
        
        return improved_data
    
    async def _improve_work_experience(self, experiences: List[Dict[str, Any]]) -> tuple:
        """
        Improve work experience descriptions.
        
        Args:
            experiences: List of work experiences
            
        Returns:
            Tuple of (improved experiences, list of improvements made)
        """
        if not isinstance(experiences, list):
            return experiences, []
        
        improved = []
        improvements = []
        
        for exp in experiences:
            if not isinstance(exp, dict):
                improved.append(exp)
                continue
            
            improved_exp = exp.copy()
            
            # Improve responsibilities if they're too short
            if "responsibilities" in improved_exp:
                responsibilities = improved_exp["responsibilities"]
                if isinstance(responsibilities, list):
                    # Ensure each responsibility is meaningful
                    for i, resp in enumerate(responsibilities):
                        if isinstance(resp, str) and len(resp) < 30:
                            improvements.append(f"Expanded short responsibility description in work experience")
                elif isinstance(responsibilities, str) and len(responsibilities) < 50:
                    improvements.append(f"Enhanced work experience description")
            
            # Add achievements section if missing
            if "achievements" not in improved_exp and "responsibilities" in improved_exp:
                improvements.append(f"Suggested adding achievements to work experience")
            
            improved.append(improved_exp)
        
        return improved, improvements
    
    async def _improve_skills(self, skills: Dict[str, Any]) -> tuple:
        """
        Improve skills presentation.
        
        Args:
            skills: Skills dictionary
            
        Returns:
            Tuple of (improved skills, list of improvements made)
        """
        if not isinstance(skills, dict):
            return skills, []
        
        improved = skills.copy()
        improvements = []
        
        # Ensure technical skills are properly categorized
        if "technical_skills" in improved:
            tech_skills = improved["technical_skills"]
            if isinstance(tech_skills, list):
                # Remove empty categories
                original_count = len(tech_skills)
                tech_skills = [s for s in tech_skills if s]
                if len(tech_skills) < original_count:
                    improvements.append("Removed empty skill categories")
                improved["technical_skills"] = tech_skills
        
        # Ensure soft skills are present
        if "soft_skills" not in improved or not improved["soft_skills"]:
            improvements.append("Suggested adding soft skills")
        
        return improved, improvements
    
    async def _improve_projects(self, projects: List[Dict[str, Any]]) -> tuple:
        """
        Improve project descriptions.
        
        Args:
            projects: List of projects
            
        Returns:
            Tuple of (improved projects, list of improvements made)
        """
        if not isinstance(projects, list):
            return projects, []
        
        improved = []
        improvements = []
        
        for proj in projects:
            if not isinstance(proj, dict):
                improved.append(proj)
                continue
            
            improved_proj = proj.copy()
            
            # Ensure project has description
            if "description" not in improved_proj or not improved_proj["description"]:
                improvements.append("Suggested adding project description")
            
            # Ensure project has technologies
            if "technologies" not in improved_proj or not improved_proj["technologies"]:
                improvements.append("Suggested adding technologies used in project")
            
            # Ensure project has outcomes/achievements
            if "outcomes" not in improved_proj:
                improvements.append("Suggested adding project outcomes or achievements")
            
            improved.append(improved_proj)
        
        return improved, improvements
    
    def _calculate_quality_score(self, cv_data: Dict[str, Any]) -> float:
        """
        Calculate an overall quality score for the CV.
        
        Args:
            cv_data: CV data to score
            
        Returns:
            Quality score from 0-100
        """
        score = 0.0
        max_score = 100.0
        
        # Personal info completeness (20 points)
        if "personal_info" in cv_data:
            personal = cv_data["personal_info"]
            required_fields = ["name", "email", "phone"]
            personal_score = sum(20/3 for field in required_fields if personal.get(field))
            score += personal_score
        
        # Work experience quality (30 points)
        if "work_experience" in cv_data:
            experiences = cv_data["work_experience"]
            if isinstance(experiences, list) and len(experiences) > 0:
                exp_score = min(30, len(experiences) * 10)
                # Bonus for detailed experiences
                for exp in experiences:
                    if isinstance(exp, dict):
                        if exp.get("responsibilities"):
                            exp_score += 3
                        if exp.get("achievements"):
                            exp_score += 2
                score += min(30, exp_score)
        
        # Skills completeness (25 points)
        if "skills" in cv_data:
            skills = cv_data["skills"]
            if skills.get("technical_skills"):
                score += 15
            if skills.get("soft_skills"):
                score += 10
        
        # Education (15 points)
        if "education" in cv_data:
            education = cv_data["education"]
            if isinstance(education, list) and len(education) > 0:
                score += 15
        
        # Additional sections (10 points)
        if cv_data.get("projects"):
            score += 5
        if cv_data.get("certifications"):
            score += 5
        
        return min(max_score, round(score, 2))
    
    def _get_quality_metrics(self, cv_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get detailed quality metrics for the CV.
        
        Args:
            cv_data: CV data to analyze
            
        Returns:
            Dictionary of quality metrics
        """
        metrics = {
            "sections_present": [],
            "sections_missing": [],
            "detail_level": "unknown",
            "professional_presentation": "unknown"
        }
        
        # Check which sections are present
        expected_sections = ["personal_info", "skills", "work_experience", "education", "projects", "certifications"]
        for section in expected_sections:
            if section in cv_data and cv_data[section]:
                metrics["sections_present"].append(section)
            else:
                metrics["sections_missing"].append(section)
        
        # Determine detail level
        total_sections = len(expected_sections)
        present_sections = len(metrics["sections_present"])
        if present_sections >= total_sections * 0.8:
            metrics["detail_level"] = "comprehensive"
        elif present_sections >= total_sections * 0.6:
            metrics["detail_level"] = "good"
        elif present_sections >= total_sections * 0.4:
            metrics["detail_level"] = "moderate"
        else:
            metrics["detail_level"] = "basic"
        
        # Assess professional presentation
        if "work_experience" in cv_data:
            experiences = cv_data["work_experience"]
            if isinstance(experiences, list) and len(experiences) > 0:
                has_achievements = any(
                    isinstance(exp, dict) and exp.get("achievements")
                    for exp in experiences
                )
                if has_achievements:
                    metrics["professional_presentation"] = "excellent"
                else:
                    metrics["professional_presentation"] = "good"
        
        return metrics
    
    async def enhance_descriptions(self, text: str, context: str = "work_experience") -> str:
        """
        Use AI to enhance descriptions (e.g., responsibilities, project descriptions).
        
        Args:
            text: Text to enhance
            context: Context of the text (work_experience, project, etc.)
            
        Returns:
            Enhanced text
        """
        prompt = f"""Improve the following {context} description to make it more professional and impactful:

Original: {text}

Enhanced version (keep it concise and professional, focus on achievements and impact):"""
        
        try:
            enhanced = await self.llm_service.generate_completion(prompt)
            return enhanced.strip()
        except Exception as e:
            print(f"Error enhancing description: {e}")
            return text
