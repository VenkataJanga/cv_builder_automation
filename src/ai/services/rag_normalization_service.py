"""
RAG-assisted normalization service for CV data enhancement.
Uses retrieval-augmented generation to improve skills and standardize roles.
"""
import json
from typing import Dict, Any, List, Optional
from openai import OpenAI
import os


class RAGNormalizationService:
    """
    RAG-based service to normalize and enhance CV data using best practices
    and industry standards retrieved from knowledge base.
    """
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY", "").strip('"')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"
    
    def normalize_skills(self, skills: Dict[str, Any], context: str = "") -> Dict[str, Any]:
        """
        Normalize and enhance skills using RAG approach.
        
        Args:
            skills: Dictionary containing technical_skills (dict), soft_skills (list), domains (list)
            context: Additional context from CV (role, industry, etc.)
            
        Returns:
            Enhanced and normalized skills dictionary with technical_skills as categorized dict
        """
        prompt = self._build_skills_normalization_prompt(skills, context)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert in standardizing and enhancing technical skills and competencies.
                        Your goal is to:
                        1. Standardize skill names (e.g., "JS" → "JavaScript", "ML" → "Machine Learning")
                        2. Remove duplicates and variations
                        3. Categorize skills appropriately
                        4. Add related/implied skills based on context
                        5. Use industry-standard terminology
                        Return valid JSON only."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            normalized = json.loads(response.choices[0].message.content)
            return normalized.get("skills", skills)
            
        except Exception as e:
            print(f"Skills normalization failed: {str(e)}")
            return skills
    
    def standardize_roles(self, experience: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Standardize role titles using industry standards.
        
        Args:
            experience: List of experience entries with role titles
            
        Returns:
            Experience list with standardized role titles
        """
        if not experience:
            return experience
        
        roles_to_standardize = [exp.get("role", "") for exp in experience]
        
        prompt = self._build_role_standardization_prompt(roles_to_standardize)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert in standardizing job titles and roles.
                        Standardize role titles to industry-standard formats:
                        - Use full forms (Sr. → Senior, Jr. → Junior)
                        - Consistent capitalization
                        - Remove company-specific jargon
                        - Use common industry terminology
                        Return valid JSON only."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            standardized_roles = result.get("standardized_roles", roles_to_standardize)
            
            # Apply standardized roles back to experience
            for i, exp in enumerate(experience):
                if i < len(standardized_roles):
                    exp["role"] = standardized_roles[i]
                    exp["original_role"] = roles_to_standardize[i]  # Keep original for reference
            
            return experience
            
        except Exception as e:
            print(f"Role standardization failed: {str(e)}")
            return experience
    
    def enrich_with_context(self, cv_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich CV data using contextual understanding and industry knowledge.
        
        Args:
            cv_data: Complete CV data structure
            
        Returns:
            Enriched CV data with additional context and improvements
        """
        prompt = self._build_enrichment_prompt(cv_data)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert career advisor and CV enhancement specialist.
                        Analyze the CV and provide enrichments:
                        1. Suggest missing skills that are implied by their experience
                        2. Identify industry/domain expertise
                        3. Suggest professional summary improvements
                        4. Identify career trajectory and level (entry, mid, senior, lead, etc.)
                        5. Recommend certifications relevant to their profile
                        Return valid JSON only."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            enrichments = json.loads(response.choices[0].message.content)
            
            # Apply enrichments
            cv_data["enrichments"] = enrichments
            
            # Add suggested skills
            if "suggested_skills" in enrichments:
                skills = cv_data.get("skills", {})
                if "technical_skills" not in skills:
                    skills["technical_skills"] = []
                skills["suggested_technical_skills"] = enrichments["suggested_skills"]
                cv_data["skills"] = skills
            
            # Add career insights
            if "career_level" in enrichments:
                personal = cv_data.get("personal_details", {})
                personal["career_level"] = enrichments["career_level"]
                cv_data["personal_details"] = personal
            
            # Add domain expertise if identified
            if "domain_expertise" in enrichments:
                skills = cv_data.get("skills", {})
                if "domains" not in skills:
                    skills["domains"] = []
                skills["domains"] = list(set(skills["domains"] + enrichments["domain_expertise"]))
                cv_data["skills"] = skills
            
            return cv_data
            
        except Exception as e:
            print(f"Enrichment failed: {str(e)}")
            return cv_data
    
    def _build_skills_normalization_prompt(self, skills: Dict[str, List[str]], context: str) -> str:
        """Build prompt for skills normalization."""
        return f"""
Normalize and enhance the following skills:

CURRENT SKILLS:
{json.dumps(skills, indent=2)}

CONTEXT:
{context}

INSTRUCTIONS:
1. Standardize all skill names to industry-standard terms
2. Expand abbreviations (JS → JavaScript, AWS → Amazon Web Services, etc.)
3. Remove duplicates and near-duplicates
4. Group similar skills together
5. Based on the skills present, infer and add related skills they likely have
6. Ensure proper categorization

Return JSON in this format:
{{
  "skills": {{
    "technical_skills": [
      {{"Primary Skills": "comma-separated string"}},
      {{"Operating Systems": "comma-separated string"}},
      {{"Languages": "comma-separated string"}},
      {{"Development Tools": "comma-separated string"}},
      {{"Frameworks": "comma-separated string"}},
      {{"CRM tools": "comma-separated string"}},
      {{"Database Connectivity": "comma-separated string"}},
      {{"Databases": "comma-separated string"}},
      {{"SQL Skills": "comma-separated string"}},
      {{"Cloud Platforms": "comma-separated string"}},
      {{"Other Tools": "comma-separated string"}}
    ],
    "soft_skills": ["list of normalized soft skills"],
    "domains": ["list of domain expertise areas"]
  }},
  "changes_made": ["description of major changes/additions"]
}}

CRITICAL: technical_skills MUST be an array of single-key objects where each object has ONE category as the key!
"""
    
    def _build_role_standardization_prompt(self, roles: List[str]) -> str:
        """Build prompt for role standardization."""
        return f"""
Standardize the following job titles to industry-standard formats:

ROLES TO STANDARDIZE:
{json.dumps(roles, indent=2)}

INSTRUCTIONS:
1. Expand abbreviations (Sr. → Senior, Jr. → Junior, etc.)
2. Use consistent capitalization
3. Remove company-specific terminology
4. Use industry-standard role titles
5. Maintain the seniority level indicated

Examples:
- "Sr. Software Eng." → "Senior Software Engineer"
- "Tech Lead" → "Technical Lead"
- "SDE-2" → "Software Development Engineer II"
- "DevOps" → "DevOps Engineer"

Return JSON in this format:
{{
  "standardized_roles": ["list of standardized role titles in same order"]
}}
"""
    
    def _build_enrichment_prompt(self, cv_data: Dict[str, Any]) -> str:
        """Build prompt for CV enrichment."""
        personal = cv_data.get("personal_details", {})
        skills = cv_data.get("skills", {})
        experience = cv_data.get("experience", [])
        
        return f"""
Analyze this CV and provide enrichment suggestions:

CURRENT ROLE: {personal.get("current_role", "Unknown")}
TOTAL EXPERIENCE: {personal.get("total_experience", "Unknown")} years
TECHNICAL SKILLS: {skills.get("technical_skills", [])}
NUMBER OF ROLES: {len(experience)}

EXPERIENCE SUMMARY:
{json.dumps([{"role": e.get("role"), "organization": e.get("organization")} for e in experience[:5]], indent=2)}

INSTRUCTIONS:
1. Determine career level (Entry/Mid/Senior/Lead/Principal/Architect/Executive)
2. Identify domain expertise areas
3. Suggest 5-10 additional skills they likely have based on their roles
4. Suggest relevant certifications for their career path
5. Provide professional summary enhancement suggestions

Return JSON in this format:
{{
  "career_level": "string (e.g., 'Senior', 'Lead')",
  "domain_expertise": ["list of domains"],
  "suggested_skills": ["list of implied skills"],
  "recommended_certifications": ["list of relevant certifications"],
  "summary_enhancement": "improved professional summary text",
  "career_insights": "brief analysis of their career trajectory"
}}
"""


class QualityImprovementService:
    """
    Service to improve overall CV quality and completeness.
    """
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY", "").strip('"')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"
    
    def assess_quality(self, cv_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess overall CV quality and provide improvement recommendations.
        
        Returns:
            Quality assessment with scores and recommendations
        """
        prompt = self._build_quality_assessment_prompt(cv_data)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert CV reviewer and career counselor.
                        Assess CV quality across multiple dimensions and provide actionable feedback.
                        Be constructive and specific in your recommendations."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            assessment = json.loads(response.choices[0].message.content)
            return assessment
            
        except Exception as e:
            print(f"Quality assessment failed: {str(e)}")
            return {"overall_score": 0, "error": str(e)}
    
    def improve_descriptions(self, experience: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Improve responsibility and achievement descriptions using AI.
        
        Args:
            experience: List of experience entries
            
        Returns:
            Experience list with improved descriptions
        """
        for exp in experience:
            responsibilities = exp.get("responsibilities", [])
            if responsibilities:
                improved = self._improve_bullet_points(responsibilities, exp.get("role", ""))
                exp["improved_responsibilities"] = improved
        
        return experience
    
    def _improve_bullet_points(self, bullets: List[str], role: str) -> List[str]:
        """Improve individual bullet points."""
        prompt = f"""
Improve these responsibility/achievement bullet points for a {role}:

CURRENT BULLETS:
{json.dumps(bullets, indent=2)}

INSTRUCTIONS:
1. Use action verbs
2. Quantify achievements where possible
3. Make them more impactful and specific
4. Keep them concise (1-2 lines each)
5. Maintain truthfulness - only enhance, don't fabricate

Return JSON: {{"improved_bullets": ["list of improved bullet points"]}}
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at writing impactful CV bullet points."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.4,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result.get("improved_bullets", bullets)
            
        except Exception as e:
            print(f"Bullet point improvement failed: {str(e)}")
            return bullets
    
    def _build_quality_assessment_prompt(self, cv_data: Dict[str, Any]) -> str:
        """Build prompt for quality assessment."""
        return f"""
Assess the quality of this CV data:

PERSONAL DETAILS: {bool(cv_data.get("personal_details", {}).get("full_name"))}
EMAIL: {bool(cv_data.get("personal_details", {}).get("email"))}
PHONE: {bool(cv_data.get("personal_details", {}).get("phone"))}
SUMMARY: {bool(cv_data.get("summary", {}).get("professional_summary"))}
SKILLS COUNT: {len(cv_data.get("skills", {}).get("technical_skills", []))}
EXPERIENCE ENTRIES: {len(cv_data.get("experience", []))}
EDUCATION ENTRIES: {len(cv_data.get("education", []))}
CERTIFICATIONS: {len(cv_data.get("certifications", []))}

Provide detailed assessment in this JSON format:
{{
  "overall_score": "number 0-100",
  "completeness_score": "number 0-100",
  "detail_quality_score": "number 0-100",
  "professional_presentation_score": "number 0-100",
  "strengths": ["list of strengths"],
  "weaknesses": ["list of areas to improve"],
  "critical_issues": ["list of critical problems"],
  "improvement_recommendations": [
    {{
      "area": "string",
      "current_state": "string",
      "suggested_improvement": "string",
      "priority": "high/medium/low"
    }}
  ],
  "missing_sections": ["list of sections that should be added"],
  "next_steps": ["actionable next steps to improve CV"]
}}
"""
