"""
Gap Detection Service

Detects missing or incomplete fields in CV data and suggests improvements.
"""
from typing import Dict, List, Any

from src.core.logging.logger import get_print_logger


print = get_print_logger(__name__)


class GapDetectionService:
    """Service for detecting gaps and missing fields in CV data."""
    
    def __init__(self):
        pass
    
    async def detect_gaps(self, cv_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detect gaps and missing fields in CV data.
        
        Args:
            cv_data: Normalized CV data
            
        Returns:
            List of gaps with field name and suggestions
        """
        gaps = []
        
        # Check personal info
        if "personal_info" in cv_data:
            personal = cv_data["personal_info"]
            if not personal.get("email"):
                gaps.append({
                    "field": "personal_info.email",
                    "severity": "high",
                    "suggestion": "Email address is required for professional communication"
                })
            if not personal.get("phone"):
                gaps.append({
                    "field": "personal_info.phone",
                    "severity": "medium",
                    "suggestion": "Phone number helps recruiters contact you easily"
                })
            if not personal.get("location"):
                gaps.append({
                    "field": "personal_info.location",
                    "severity": "medium",
                    "suggestion": "Location information helps with job matching"
                })
        
        # Check work experience
        if "work_experience" in cv_data:
            experiences = cv_data["work_experience"]
            if isinstance(experiences, list):
                for i, exp in enumerate(experiences):
                    if isinstance(exp, dict):
                        if not exp.get("responsibilities"):
                            gaps.append({
                                "field": f"work_experience[{i}].responsibilities",
                                "severity": "high",
                                "suggestion": "Add detailed responsibilities and achievements for this role"
                            })
                        if not exp.get("end_date") and not exp.get("current", False):
                            gaps.append({
                                "field": f"work_experience[{i}].end_date",
                                "severity": "medium",
                                "suggestion": "Specify end date or mark as current position"
                            })
        
        # Check skills
        if "skills" in cv_data:
            skills = cv_data["skills"]
            if not skills.get("technical_skills"):
                gaps.append({
                    "field": "skills.technical_skills",
                    "severity": "high",
                    "suggestion": "Technical skills are crucial for technical roles"
                })
            if not skills.get("soft_skills"):
                gaps.append({
                    "field": "skills.soft_skills",
                    "severity": "medium",
                    "suggestion": "Soft skills demonstrate your ability to work in teams"
                })
        
        # Check education
        if not cv_data.get("education"):
            gaps.append({
                "field": "education",
                "severity": "high",
                "suggestion": "Education background is important for most positions"
            })
        
        # Check certifications
        if not cv_data.get("certifications"):
            gaps.append({
                "field": "certifications",
                "severity": "low",
                "suggestion": "Professional certifications can strengthen your profile"
            })
        
        # Check projects
        if not cv_data.get("projects"):
            gaps.append({
                "field": "projects",
                "severity": "medium",
                "suggestion": "Project experience demonstrates practical skills"
            })
        
        return gaps
    
    async def suggest_missing_fields(self, cv_data: Dict[str, Any], original_text: str) -> Dict[str, Any]:
        """
        Use AI to suggest content for missing fields based on the original CV text.
        
        Args:
            cv_data: Normalized CV data
            original_text: Original CV text
            
        Returns:
            Dictionary of field suggestions
        """
        # Create prompt for AI suggestion
        prompt = f"""Analyze the following CV text and suggest missing fields that should be added:

CV Data:
{cv_data}

Original CV Text:
{original_text}

Based on the CV text, suggest content for any missing or incomplete fields.
Return a JSON object with suggested fields and their values.
Focus on:
- Missing contact information
- Incomplete work experience details
- Missing skills that are mentioned in the text
- Educational details not captured
- Certifications or achievements mentioned but not structured

Return format:
{{
    "field_name": "suggested_value",
    ...
}}
"""
        
        try:
            # Use LLM to generate suggestions
            response = await self.llm_service.generate_completion(prompt)
            
            # Parse response
            import json
            try:
                suggestions = json.loads(response)
                return suggestions if isinstance(suggestions, dict) else {}
            except json.JSONDecodeError:
                # If response is not valid JSON, return as is
                return {"raw_suggestions": response}
        except Exception as e:
            print(f"Error generating suggestions: {e}")
            return {}
    
    async def analyze_completeness(self, cv_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze the completeness of the CV data.
        
        Args:
            cv_data: CV data to analyze
            
        Returns:
            Completeness analysis with score and recommendations
        """
        total_fields = 0
        complete_fields = 0
        
        # Define expected fields and their importance weights
        expected_fields = {
            "personal_info": {"weight": 2, "subfields": ["name", "email", "phone", "location"]},
            "skills": {"weight": 3, "subfields": ["technical_skills", "soft_skills"]},
            "work_experience": {"weight": 3, "subfields": ["title", "company", "start_date", "responsibilities"]},
            "education": {"weight": 2, "subfields": ["degree", "institution", "year"]},
            "certifications": {"weight": 1, "subfields": ["name", "issuer", "date"]},
            "projects": {"weight": 1, "subfields": ["name", "description", "technologies"]}
        }
        
        recommendations = []
        
        for field, config in expected_fields.items():
            weight = config["weight"]
            total_fields += weight
            
            if field in cv_data and cv_data[field]:
                complete_fields += weight
            else:
                recommendations.append(f"Add {field} section")
        
        # Calculate completeness score
        score = (complete_fields / total_fields * 100) if total_fields > 0 else 0
        
        return {
            "completeness_score": round(score, 2),
            "total_sections": len(expected_fields),
            "complete_sections": sum(1 for f in expected_fields if f in cv_data and cv_data[f]),
            "recommendations": recommendations,
            "quality_level": "excellent" if score >= 90 else "good" if score >= 70 else "fair" if score >= 50 else "needs_improvement"
        }
