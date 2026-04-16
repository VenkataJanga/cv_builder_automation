"""
CV Workflow Orchestrator - Manages the complete CV processing pipeline.
Implements: Upload → AI Extraction → Schema Mapping → RAG Enrichment → Validation → Preview → Edit Loop
"""
import json
from typing import Dict, Any, Optional, List
from src.core.logging.logger import get_print_logger

# Load environment variables first
from src.core.env_loader import load_environment_variables
load_environment_variables()

from src.ai.services.cv_extraction_service import CVExtractionService
from src.ai.services.rag_normalization_service import RAGNormalizationService, QualityImprovementService
from src.infrastructure.parsers.deduplication_utils import deduplicate_cv_data


print = get_print_logger(__name__)


class CVWorkflowOrchestrator:
    """
    Orchestrates the complete CV processing workflow with AI-based extraction,
    RAG-assisted normalization, validation, and quality improvement.
    """
    
    def __init__(self):
        """Initialize all services needed for CV processing."""
        self.extraction_service = None
        self.rag_service = None
        self.quality_service = None
        self.services_available = False
        
        # Always initialize the basic parser as fallback
        from src.infrastructure.parsers.resume_parser import ResumeParser
        self.basic_parser = ResumeParser()
        
        try:
            self.extraction_service = CVExtractionService()
            self.rag_service = RAGNormalizationService()
            self.quality_service = QualityImprovementService()
            self.services_available = True
        except Exception as e:
            print(f"Warning: Some AI services unavailable: {e}")
    
    def process_cv(self, cv_text: str, workflow_options: Optional[Dict[str, bool]] = None) -> Dict[str, Any]:
        """
        Process CV through the complete workflow pipeline.
        
        Args:
            cv_text: Raw text extracted from CV document
            workflow_options: Dict to enable/disable workflow steps
                - enable_extraction: AI-based extraction (default True)
                - enable_section_detection: Detect CV sections (default True)
                - enable_rag_normalization: RAG-assisted skill/role normalization (default True)
                - enable_gap_detection: Detect missing fields (default True)
                - enable_quality_improvement: Quality assessment and improvement (default True)
                - enable_auto_suggestions: Auto-suggest missing fields (default True)
        
        Returns:
            Complete workflow result with extracted, enriched, and validated CV data
        """
        # Default options
        options = {
            "enable_extraction": True,
            "enable_section_detection": True,
            "enable_rag_normalization": True,
            "enable_gap_detection": True,
            "enable_quality_improvement": True,
            "enable_auto_suggestions": True
        }
        if workflow_options:
            options.update(workflow_options)
        
        workflow_result = {
            "status": "processing",
            "steps_completed": [],
            "cv_data": {},
            "metadata": {},
            "validation": {},
            "suggestions": {},
            "errors": []
        }
        
        try:
            # Step 1: AI-based structured extraction
            if options["enable_extraction"]:
                print("[Step 1] AI-based extraction...")
                if self.extraction_service:
                    cv_data = self.extraction_service.extract_structured_cv_data(cv_text)
                    workflow_result["cv_data"] = cv_data
                    workflow_result["steps_completed"].append("ai_extraction")
                    workflow_result["metadata"]["extraction_method"] = "AI"
                    print("[OK] Extraction complete")
                else:
                    # Use fallback extraction when AI service not available
                    print("[WARN] AI service unavailable, using fallback extraction...")
                    cv_data = self._fallback_extraction(cv_text)
                    workflow_result["cv_data"] = cv_data
                    workflow_result["steps_completed"].append("fallback_extraction")
                    workflow_result["metadata"]["extraction_method"] = "Fallback"
                    workflow_result["warnings"] = ["AI extraction unavailable, using basic extraction"]
                    print("[OK] Fallback extraction complete")
                
                # Deduplicate extracted data
                print("[Deduplicating] Removing duplicate entries...")
                cv_data = deduplicate_cv_data(cv_data)
                workflow_result["cv_data"] = cv_data
                workflow_result["steps_completed"].append("deduplication")
                print("[OK] Deduplication complete")
            else:
                workflow_result["cv_data"] = {"error": "Extraction disabled"}
                workflow_result["errors"].append("Extraction was disabled")
                return workflow_result
            
            # Step 2: Section detection
            if options["enable_section_detection"]:
                print("[Step 2] Section detection...")
                section_info = self._detect_sections(cv_data)
                workflow_result["metadata"]["sections_detected"] = section_info
                workflow_result["steps_completed"].append("section_detection")
                print(f"[OK] Detected {len(section_info['present_sections'])} sections")
            
            # Step 3: Schema mapping (validate against canonical schema)
            print("[Step 3] Schema mapping...")
            schema_validation = self._validate_schema(cv_data)
            workflow_result["validation"]["schema_validation"] = schema_validation
            workflow_result["steps_completed"].append("schema_mapping")
            print("[OK] Schema mapping complete")
            
            # Step 4: RAG-assisted normalization
            if options["enable_rag_normalization"]:
                print("[Step 4] RAG-assisted normalization...")
                cv_data = self._apply_rag_normalization(cv_data)
                workflow_result["cv_data"] = cv_data
                workflow_result["steps_completed"].append("rag_normalization")
                print("[OK] Normalization complete")
            
            # Step 5: Gap detection
            if options["enable_gap_detection"]:
                print("[Step 5] Gap detection...")
                if self.extraction_service:
                    gaps = self.extraction_service.detect_gaps(cv_data)
                else:
                    gaps = self._basic_gap_detection(cv_data)
                workflow_result["validation"]["gaps"] = gaps
                workflow_result["steps_completed"].append("gap_detection")
                print(f"[OK] Found {len(gaps['missing_required_fields'])} missing required fields")
            
            # Step 6: Auto-suggest missing fields
            if options["enable_auto_suggestions"]:
                print("[Step 6] Auto-suggesting missing fields...")
                suggestions = self._generate_suggestions(cv_data, gaps if options["enable_gap_detection"] else {})
                workflow_result["suggestions"] = suggestions
                workflow_result["steps_completed"].append("auto_suggestions")
                print(f"[OK] Generated {len(suggestions.get('field_suggestions', []))} suggestions")
            
            # Step 7: Quality improvement
            if options["enable_quality_improvement"] and self.quality_service:
                print("[Step 7] Quality assessment...")
                quality_assessment = self.quality_service.assess_quality(cv_data)
                workflow_result["validation"]["quality_assessment"] = quality_assessment
                workflow_result["steps_completed"].append("quality_assessment")
                print(f"[OK] Quality score: {quality_assessment.get('overall_score', 0)}/100")
                
                # Optionally improve descriptions
                if cv_data.get("experience"):
                    print("[Improving] experience descriptions...")
                    improved_experience = self.quality_service.improve_descriptions(cv_data["experience"])
                    workflow_result["cv_data"]["experience"] = improved_experience
                    print("[OK] Descriptions improved")
            
            # Step 8: Final validation
            print("[Step 8] Final validation...")
            final_validation = self._perform_final_validation(cv_data, workflow_result)
            workflow_result["validation"]["final_validation"] = final_validation
            workflow_result["steps_completed"].append("final_validation")
            
            workflow_result["status"] = "completed"
            workflow_result["metadata"]["total_steps"] = len(workflow_result["steps_completed"])
            
            print(f"\n[SUCCESS] Workflow complete! {len(workflow_result['steps_completed'])} steps executed successfully")
            
            return workflow_result
            
        except Exception as e:
            workflow_result["status"] = "error"
            workflow_result["errors"].append(str(e))
            print(f"[ERROR] Workflow error: {str(e)}")
            return workflow_result
    
    def _fallback_extraction(self, cv_text: str) -> Dict[str, Any]:
        """
        Fallback extraction method when AI service is unavailable.
        Uses the improved ResumeParser for comprehensive extraction.
        
        Args:
            cv_text: Raw CV text
            
        Returns:
            Parsed CV data structure
        """
        # Use the improved ResumeParser which has better extraction logic
        cv_data = self.basic_parser.parse(cv_text)
        
        return cv_data
    
    def _detect_sections(self, cv_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect which sections are present in the CV data.
        
        Returns:
            Dictionary with section detection results
        """
        section_map = {
            "personal_details": cv_data.get("personal_details", {}),
            "summary": cv_data.get("summary", {}),
            "skills": cv_data.get("skills", {}),
            "experience": cv_data.get("experience", []),
            "project_experience": cv_data.get("project_experience", []),
            "education": cv_data.get("education", []),
            "certifications": cv_data.get("certifications", []),
            "publications": cv_data.get("publications", []),
            "awards": cv_data.get("awards", []),
            "languages": cv_data.get("languages", [])
        }
        
        present_sections = []
        missing_sections = []
        
        for section_name, section_data in section_map.items():
            if isinstance(section_data, dict):
                # For dict sections, check if any keys have values
                if any(section_data.values()):
                    present_sections.append(section_name)
                else:
                    missing_sections.append(section_name)
            elif isinstance(section_data, list):
                # For list sections, check if non-empty
                if len(section_data) > 0:
                    present_sections.append(section_name)
                else:
                    missing_sections.append(section_name)
        
        return {
            "present_sections": present_sections,
            "missing_sections": missing_sections,
            "section_completeness": len(present_sections) / len(section_map) * 100
        }
    
    def _validate_schema(self, cv_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate CV data against canonical schema.
        
        Returns:
            Schema validation results
        """
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check required fields
        required_fields = {
            "personal_details": ["full_name", "email"],
            "summary": [],
            "skills": [],
            "experience": [],
            "education": []
        }
        
        for section, fields in required_fields.items():
            if section not in cv_data:
                validation_result["errors"].append(f"Missing required section: {section}")
                validation_result["valid"] = False
            else:
                section_data = cv_data[section]
                if isinstance(section_data, dict):
                    for field in fields:
                        if not section_data.get(field):
                            validation_result["warnings"].append(f"Missing recommended field: {section}.{field}")
        
        # Validate data types
        if "experience" in cv_data and not isinstance(cv_data["experience"], list):
            validation_result["errors"].append("experience must be a list")
            validation_result["valid"] = False
        
        if "education" in cv_data and not isinstance(cv_data["education"], list):
            validation_result["errors"].append("education must be a list")
            validation_result["valid"] = False
        
        return validation_result
    
    def _apply_rag_normalization(self, cv_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply RAG-assisted normalization to improve skills and standardize roles.
        
        Returns:
            Normalized CV data
        """
        if not self.rag_service:
            return cv_data
        
        # Normalize skills
        if cv_data.get("skills"):
            context = f"Role: {cv_data.get('personal_details', {}).get('current_role', 'Unknown')}"
            normalized_skills = self.rag_service.normalize_skills(cv_data["skills"], context)
            cv_data["skills"] = normalized_skills
        
        # Standardize roles
        if cv_data.get("experience"):
            standardized_experience = self.rag_service.standardize_roles(cv_data["experience"])
            cv_data["experience"] = standardized_experience
        
        # Enrich with contextual information
        enriched_data = self.rag_service.enrich_with_context(cv_data)
        
        return enriched_data
    
    def _basic_gap_detection(self, cv_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Basic gap detection when AI service is not available.
        
        Returns:
            Dictionary with missing fields
        """
        missing_required = []
        missing_recommended = []
        
        # Check personal details
        personal = cv_data.get("personal_details", {})
        if not personal.get("full_name"):
            missing_required.append("personal_details.full_name")
        if not personal.get("email"):
            missing_required.append("personal_details.email")
        if not personal.get("phone"):
            missing_recommended.append("personal_details.phone")
        
        # Check summary
        if not cv_data.get("summary", {}).get("professional_summary"):
            missing_recommended.append("summary.professional_summary")
        
        # Check skills
        if not cv_data.get("skills", {}).get("technical_skills"):
            missing_required.append("skills.technical_skills")
        
        # Check experience
        if not cv_data.get("experience") or len(cv_data.get("experience", [])) == 0:
            missing_recommended.append("experience")
        
        # Check education
        if not cv_data.get("education") or len(cv_data.get("education", [])) == 0:
            missing_recommended.append("education")
        
        return {
            "missing_required_fields": missing_required,
            "missing_recommended_fields": missing_recommended,
            "gaps_detected": len(missing_required) + len(missing_recommended)
        }
    
    def _generate_suggestions(self, cv_data: Dict[str, Any], gaps: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate auto-suggestions for missing or incomplete fields.
        
        Returns:
            Dictionary with suggestions
        """
        suggestions = {
            "field_suggestions": [],
            "content_suggestions": [],
            "priority_actions": []
        }
        
        # Suggest based on gaps
        if gaps.get("missing_required_fields"):
            for field in gaps["missing_required_fields"]:
                suggestions["field_suggestions"].append({
                    "field": field,
                    "type": "required",
                    "suggestion": f"Please provide your {field}",
                    "priority": "high"
                })
                suggestions["priority_actions"].append(f"Add {field}")
        
        if gaps.get("missing_recommended_fields"):
            for field in gaps["missing_recommended_fields"]:
                suggestions["field_suggestions"].append({
                    "field": field,
                    "type": "recommended",
                    "suggestion": f"Consider adding {field} to strengthen your CV",
                    "priority": "medium"
                })
        
        # Content-based suggestions
        experience = cv_data.get("experience", [])
        if experience:
            for i, exp in enumerate(experience):
                if not exp.get("responsibilities") or len(exp.get("responsibilities", [])) < 3:
                    suggestions["content_suggestions"].append({
                        "section": "experience",
                        "index": i,
                        "role": exp.get("role", "Unknown"),
                        "suggestion": "Add more detailed responsibilities and achievements (aim for 4-6 bullet points)"
                    })
        
        # Check for missing professional summary
        if not cv_data.get("summary", {}).get("professional_summary"):
            suggestions["priority_actions"].append("Add a professional summary (2-3 sentences)")
            suggestions["field_suggestions"].append({
                "field": "professional_summary",
                "type": "required",
                "suggestion": "Add a compelling professional summary highlighting your key strengths and experience",
                "priority": "high"
            })
        
        # Check for minimal skills
        skills_count = len(cv_data.get("skills", {}).get("technical_skills", []))
        if skills_count < 5:
            suggestions["content_suggestions"].append({
                "section": "skills",
                "suggestion": f"You have only {skills_count} technical skills listed. Consider adding more relevant skills"
            })
        
        # Suggest certifications if none present
        if not cv_data.get("certifications") or len(cv_data.get("certifications", [])) == 0:
            suggestions["content_suggestions"].append({
                "section": "certifications",
                "suggestion": "Consider adding relevant certifications to strengthen your profile"
            })
        
        return suggestions
    
    def _perform_final_validation(self, cv_data: Dict[str, Any], workflow_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform final validation before allowing preview/edit.
        
        Returns:
            Final validation status
        """
        validation = {
            "ready_for_preview": True,
            "blocking_issues": [],
            "warnings": [],
            "completeness_percentage": 0
        }
        
        # Check critical fields
        personal = cv_data.get("personal_details", {})
        if not personal.get("full_name"):
            validation["blocking_issues"].append("Full name is required")
            validation["ready_for_preview"] = False
        
        if not personal.get("email"):
            validation["blocking_issues"].append("Email is required")
            validation["ready_for_preview"] = False
        
        # Calculate completeness
        total_sections = 10
        present_sections = len(workflow_result.get("metadata", {}).get("sections_detected", {}).get("present_sections", []))
        validation["completeness_percentage"] = (present_sections / total_sections) * 100
        
        # Add warnings for low completeness
        if validation["completeness_percentage"] < 40:
            validation["warnings"].append("CV appears incomplete. Consider adding more sections.")
        
        # Check quality score if available
        quality = workflow_result.get("validation", {}).get("quality_assessment", {})
        if quality.get("overall_score", 0) < 50:
            validation["warnings"].append("CV quality score is below 50. Consider improving content quality.")
        
        return validation
    
    def preview_cv(self, workflow_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a preview of the processed CV data.
        
        Args:
            workflow_result: Result from process_cv()
            
        Returns:
            Preview-ready CV data with formatting
        """
        cv_data = workflow_result.get("cv_data", {})
        
        preview = {
            "preview_ready": True,
            "formatted_cv": self._format_cv_for_preview(cv_data),
            "metadata": workflow_result.get("metadata", {}),
            "suggestions": workflow_result.get("suggestions", {}),
            "validation": workflow_result.get("validation", {})
        }
        
        return preview
    
    def _format_cv_for_preview(self, cv_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format CV data for preview display.
        
        Returns:
            Formatted CV data ready for UI display
        """
        formatted = {
            "sections": []
        }
        
        # Add sections
        if cv_data.get("personal_details"):
            formatted["sections"].append({"name": "Personal Details", "type": "personal", "data": cv_data["personal_details"], "editable": True})
        
        if cv_data.get("summary"):
            formatted["sections"].append({"name": "Professional Summary", "type": "summary", "data": cv_data["summary"], "editable": True})
        
        if cv_data.get("skills"):
            formatted["sections"].append({"name": "Skills", "type": "skills", "data": cv_data["skills"], "editable": True})
        
        if cv_data.get("experience"):
            formatted["sections"].append({"name": "Work Experience", "type": "experience", "data": cv_data["experience"], "editable": True})
        
        if cv_data.get("project_experience"):
            formatted["sections"].append({"name": "Projects", "type": "projects", "data": cv_data["project_experience"], "editable": True})
        
        if cv_data.get("education"):
            formatted["sections"].append({"name": "Education", "type": "education", "data": cv_data["education"], "editable": True})
        
        if cv_data.get("certifications"):
            formatted["sections"].append({"name": "Certifications", "type": "certifications", "data": cv_data["certifications"], "editable": True})
        
        return formatted
    
    def apply_edits(self, cv_data: Dict[str, Any], edits: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply user edits to CV data and re-validate.
        
        Args:
            cv_data: Current CV data
            edits: Dictionary of edits to apply
            
        Returns:
            Updated CV data after applying edits
        """
        # Apply edits
        for section_name, updated_data in edits.items():
            if section_name in cv_data:
                cv_data[section_name] = updated_data
        
        # Re-validate
        validation = self._validate_schema(cv_data)
        
        if self.extraction_service:
            gaps = self.extraction_service.detect_gaps(cv_data)
        else:
            gaps = self._basic_gap_detection(cv_data)
        
        return {
            "cv_data": cv_data,
            "validation": validation,
            "gaps": gaps,
            "edits_applied": True
        }
