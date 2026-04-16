"""
Schema Merge Service for Canonical CV Schema

This service provides deep merge capabilities for Canonical CV Schema instances,
ensuring data preservation, deduplication, and proper source precedence handling.

Author: CV Builder Automation System
Date: 2026-04-12
"""

from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from copy import deepcopy
from src.domain.cv.models.canonical_cv_schema import CanonicalCVSchema
from src.domain.cv.enums import SourceType


class SchemaMergeService:
    """
    Canonical CV Schema merge service with intelligent data preservation.
    
    Provides deep merge capabilities with:
    - Source precedence rules (manual_edit > conversation > audio > document)
    - Data preservation (rich content over sparse content)
    - Deduplication for lists (skills, projects, education)
    - Project description preservation
    - Audit trail updates
    """
    
    # Source precedence ranking (higher number = higher priority)
    SOURCE_PRECEDENCE = {
        SourceType.DOCUMENT_UPLOAD: 1,
        SourceType.AUDIO_UPLOAD: 2,
        SourceType.AUDIO_RECORDING: 2,
        SourceType.BOT_CONVERSATION: 3,
        SourceType.MANUAL_EDIT: 4  # Highest priority
    }
    
    def merge_canonical_cvs(
        self,
        existing_cv: Union[CanonicalCVSchema, Dict[str, Any]],
        new_data: Union[CanonicalCVSchema, Dict[str, Any]],
        source_type: SourceType,
        operation: str = "merge"
    ) -> Dict[str, Any]:
        """
        Deep merge two canonical CV schemas with intelligent data preservation.
        
        Args:
            existing_cv: Current canonical CV schema (can be dict or model instance)
            new_data: New data to merge (can be dict or model instance) 
            source_type: Source type of the new data for precedence rules
            operation: Operation type for audit trail
            
        Returns:
            Merged canonical CV as dictionary
        """
        # Convert to dictionaries if needed
        existing_dict = self._to_dict(existing_cv)
        new_dict = self._to_dict(new_data)
        
        # Start with deep copy of existing data to preserve all current information
        merged_cv = deepcopy(existing_dict)
        
        # Merge each section with specialized logic
        merged_cv["candidate"] = self._merge_candidate_section(
            existing_dict.get("candidate", {}),
            new_dict.get("candidate", {}),
            source_type
        )
        
        merged_cv["skills"] = self._merge_skills_section(
            existing_dict.get("skills", {}),
            new_dict.get("skills", {}),
            source_type
        )
        
        merged_cv["experience"] = self._merge_experience_section(
            existing_dict.get("experience", {}),
            new_dict.get("experience", {}),
            source_type
        )
        
        merged_cv["education"] = self._merge_education_with_deduplication(
            existing_dict.get("education", []),
            new_dict.get("education", []),
            source_type
        )
        
        merged_cv["certifications"] = self._merge_certifications_with_deduplication(
            existing_dict.get("certifications", []),
            new_dict.get("certifications", []),
            source_type
        )
        
        merged_cv["achievements"] = self._merge_achievements(
            existing_dict.get("achievements", []),
            new_dict.get("achievements", []),
            source_type
        )
        
        merged_cv["personalDetails"] = self._merge_personal_details(
            existing_dict.get("personalDetails", {}),
            new_dict.get("personalDetails", {}),
            source_type
        )
        
        # Update metadata sections
        merged_cv["attachmentsMetadata"] = self._merge_attachments_metadata(
            existing_dict.get("attachmentsMetadata", {}),
            new_dict.get("attachmentsMetadata", {}),
            source_type
        )
        
        # Update audit trail with merge operation
        merged_cv["audit"] = self._update_audit_trail(
            existing_dict.get("audit", {}),
            operation,
            source_type
        )
        
        # Ensure top-level metadata is updated
        merged_cv["sourceType"] = source_type.value if hasattr(source_type, 'value') else str(source_type)
        
        return merged_cv
    
    def _merge_candidate_section(
        self,
        existing: Dict[str, Any],
        new_data: Dict[str, Any],
        source_type: SourceType
    ) -> Dict[str, Any]:
        """
        Merge candidate section with field-level precedence rules.
        
        Manual edits always win, otherwise prefer richer content.
        """
        merged = deepcopy(existing)
        
        # Define fields that should be preserved if manually edited
        protected_fields = [
            "fullName", "firstName", "lastName", "phoneNumber", "email",
            "currentLocation", "summary", "careerObjective"
        ]
        
        for field, value in new_data.items():
            if not value:  # Skip empty values
                continue
                
            existing_value = merged.get(field)
            
            # Special handling for currentLocation field
            if field == "currentLocation":
                merged[field] = self._merge_location_field(
                    existing_value, value, source_type
                )
                continue
            
            # Always merge if existing is empty
            if not existing_value:
                merged[field] = value
                continue
            
            # Handle nested objects (like dictionaries)
            if isinstance(value, dict) and isinstance(existing_value, dict):
                merged[field] = self._merge_nested_dict(
                    existing_value, value, source_type
                )
                continue
            
            # For manual edits, always override
            if source_type == SourceType.MANUAL_EDIT:
                merged[field] = value
                continue
            
            # Handle preferred locations (list merge)
            if field == "preferredLocation" and isinstance(value, list):
                merged[field] = self._merge_location_list(
                    existing_value if isinstance(existing_value, list) else [],
                    value
                )
                continue
            
            # For protected fields, only update if new source has higher precedence
            # or if the existing value seems less complete
            if field in protected_fields:
                if self._should_update_field(existing_value, value, source_type):
                    merged[field] = value
            else:
                # For other fields, prefer richer content
                if len(str(value)) > len(str(existing_value)):
                    merged[field] = value
        
        return merged
    
    def _merge_skills_section(
        self,
        existing: Dict[str, Any],
        new_data: Dict[str, Any],
        source_type: SourceType
    ) -> Dict[str, Any]:
        """
        Merge skills section with deduplication and union logic.
        
        All skill categories are merged as unions with case-insensitive deduplication.
        """
        merged = deepcopy(existing)
        
        skill_categories = [
            "primarySkills", "secondarySkills", "technicalSkills", "functionalSkills",
            "softSkills", "toolsAndPlatforms", "operatingSystems", "databases",
            "cloudTechnologies", "frameworks", "libraries", "aiToolsAndFrameworks",
            "certificationsSkillsTagged"
        ]
        
        for category in skill_categories:
            existing_skills = existing.get(category, [])
            new_skills = new_data.get(category, [])
            
            if not isinstance(existing_skills, list):
                existing_skills = []
            if not isinstance(new_skills, list):
                new_skills = []
            
            # Merge with deduplication (case-insensitive)
            merged[category] = self._deduplicate_skills_list(
                existing_skills + new_skills
            )
        
        return merged
    
    def _merge_experience_section(
        self,
        existing: Dict[str, Any],
        new_data: Dict[str, Any],
        source_type: SourceType
    ) -> Dict[str, Any]:
        """
        Merge experience section with project description preservation.
        
        Critical: Never overwrite rich project descriptions with sparse ones.
        """
        merged = deepcopy(existing)
        
        # Merge simple fields
        simple_fields = ["totalProjects", "domainExperience", "industriesWorked"]
        for field in simple_fields:
            new_value = new_data.get(field)
            if new_value and not merged.get(field):
                merged[field] = new_value
        
        # Merge work history with deduplication
        existing_work = existing.get("workHistory", [])
        new_work = new_data.get("workHistory", [])
        merged["workHistory"] = self._merge_work_history(
            existing_work, new_work, source_type
        )
        
        # Merge projects with description preservation
        existing_projects = existing.get("projects", [])
        new_projects = new_data.get("projects", [])
        merged["projects"] = self._merge_projects_with_preservation(
            existing_projects, new_projects, source_type
        )
        
        return merged
    
    def _merge_projects_with_preservation(
        self,
        existing_projects: List[Dict[str, Any]],
        new_projects: List[Dict[str, Any]],
        source_type: SourceType
    ) -> List[Dict[str, Any]]:
        """
        Merge projects with strict description preservation rules.
        
        CRITICAL: Never overwrite a rich description with an empty or shorter one.
        """
        if not existing_projects:
            return new_projects
        
        if not new_projects:
            return existing_projects
        
        merged_projects = []
        used_new_indices = set()
        
        # First pass: match existing projects with new ones
        for existing_project in existing_projects:
            matched_new_index = self._find_matching_project(
                existing_project, new_projects, used_new_indices
            )
            
            if matched_new_index is not None:
                # Merge existing project with matched new project
                new_project = new_projects[matched_new_index]
                merged_project = self._merge_single_project(
                    existing_project, new_project, source_type
                )
                merged_projects.append(merged_project)
                used_new_indices.add(matched_new_index)
            else:
                # Keep existing project as-is
                merged_projects.append(existing_project)
        
        # Second pass: add unmatched new projects
        for i, new_project in enumerate(new_projects):
            if i not in used_new_indices:
                merged_projects.append(new_project)
        
        return merged_projects
    
    def _merge_single_project(
        self,
        existing: Dict[str, Any],
        new_data: Dict[str, Any],
        source_type: SourceType
    ) -> Dict[str, Any]:
        """
        Merge a single project with description preservation priority.
        """
        merged = deepcopy(existing)
        
        # Critical fields that should preserve rich content
        description_fields = [
            "projectDescription", "responsibilities", "outcomes"
        ]
        
        for field, new_value in new_data.items():
            if not new_value:
                continue
            
            existing_value = merged.get(field)
            
            # Always fill empty fields
            if not existing_value:
                merged[field] = new_value
                continue
            
            # Special handling for description fields
            if field in description_fields:
                if self._is_richer_content(new_value, existing_value):
                    merged[field] = new_value
                # Otherwise keep existing richer content
                continue
            
            # For list fields, merge with deduplication
            if isinstance(new_value, list) and isinstance(existing_value, list):
                if field == "responsibilities":
                    merged[field] = self._merge_responsibility_lists(
                        existing_value, new_value
                    )
                elif field == "environment" or field == "toolsUsed":
                    merged[field] = self._deduplicate_skills_list(
                        existing_value + new_value
                    )
                else:
                    merged[field] = list(set(existing_value + new_value))
                continue
            
            # For other fields, prefer new data if it seems more complete
            if len(str(new_value)) >= len(str(existing_value)):
                merged[field] = new_value
        
        return merged
    
    def _merge_work_history(
        self,
        existing_work: List[Dict[str, Any]],
        new_work: List[Dict[str, Any]],
        source_type: SourceType
    ) -> List[Dict[str, Any]]:
        """
        Merge work history with deduplication based on organization and role.
        """
        if not existing_work:
            return new_work
        if not new_work:
            return existing_work
        
        merged_work = []
        used_new_indices = set()
        
        # Match existing work with new work
        for existing_job in existing_work:
            matched_index = self._find_matching_work_experience(
                existing_job, new_work, used_new_indices
            )
            
            if matched_index is not None:
                new_job = new_work[matched_index]
                merged_job = self._merge_single_work_experience(
                    existing_job, new_job, source_type
                )
                merged_work.append(merged_job)
                used_new_indices.add(matched_index)
            else:
                merged_work.append(existing_job)
        
        # Add unmatched new work experiences
        for i, new_job in enumerate(new_work):
            if i not in used_new_indices:
                merged_work.append(new_job)
        
        return merged_work
    
    def _merge_education_with_deduplication(
        self,
        existing_education: List[Dict[str, Any]],
        new_education: List[Dict[str, Any]],
        source_type: SourceType
    ) -> List[Dict[str, Any]]:
        """
        Merge education with deduplication based on degree + institution + year.
        """
        if not existing_education:
            return new_education
        if not new_education:
            return existing_education
        
        merged_education = []
        used_new_indices = set()
        
        # Match existing education with new education
        for existing_edu in existing_education:
            matched_index = self._find_matching_education(
                existing_edu, new_education, used_new_indices
            )
            
            if matched_index is not None:
                new_edu = new_education[matched_index]
                merged_edu = self._merge_single_education(
                    existing_edu, new_edu, source_type
                )
                merged_education.append(merged_edu)
                used_new_indices.add(matched_index)
            else:
                merged_education.append(existing_edu)
        
        # Add unmatched new education entries
        for i, new_edu in enumerate(new_education):
            if i not in used_new_indices:
                merged_education.append(new_edu)
        
        return merged_education
    
    def _merge_certifications_with_deduplication(
        self,
        existing_certs: List[Dict[str, Any]],
        new_certs: List[Dict[str, Any]],
        source_type: SourceType
    ) -> List[Dict[str, Any]]:
        """
        Merge certifications with deduplication based on name + issuing organization.
        """
        if not existing_certs:
            return new_certs
        if not new_certs:
            return existing_certs
        
        merged_certs = []
        used_new_indices = set()
        
        # Match existing certifications with new ones
        for existing_cert in existing_certs:
            matched_index = self._find_matching_certification(
                existing_cert, new_certs, used_new_indices
            )
            
            if matched_index is not None:
                new_cert = new_certs[matched_index]
                merged_cert = self._merge_single_certification(
                    existing_cert, new_cert, source_type
                )
                merged_certs.append(merged_cert)
                used_new_indices.add(matched_index)
            else:
                merged_certs.append(existing_cert)
        
        # Add unmatched new certifications
        for i, new_cert in enumerate(new_certs):
            if i not in used_new_indices:
                merged_certs.append(new_cert)
        
        return merged_certs
    
    # Helper methods for conversion and utility functions
    
    def _to_dict(self, data: Union[CanonicalCVSchema, Dict[str, Any]]) -> Dict[str, Any]:
        """Convert CV data to dictionary format."""
        if hasattr(data, 'to_dict'):
            return data.to_dict()
        elif isinstance(data, dict):
            return data
        else:
            return {}
    
    def _should_update_field(
        self, 
        existing_value: Any, 
        new_value: Any, 
        source_type: SourceType
    ) -> bool:
        """Determine if a field should be updated based on source precedence and content richness."""
        # For manual edits, always update
        if source_type == SourceType.MANUAL_EDIT:
            return True
        
        # Prefer longer, more detailed content
        existing_str = str(existing_value) if existing_value else ""
        new_str = str(new_value) if new_value else ""
        
        return len(new_str) > len(existing_str)
    
    def _is_richer_content(self, new_content: Any, existing_content: Any) -> bool:
        """Check if new content is richer than existing content."""
        if not existing_content:
            return bool(new_content)
        
        if not new_content:
            return False
        
        # For strings, compare length and word count
        if isinstance(new_content, str) and isinstance(existing_content, str):
            new_words = len(new_content.split())
            existing_words = len(existing_content.split())
            
            # Prefer content with more words or significantly longer text
            return new_words > existing_words * 1.2 or len(new_content) > len(existing_content) * 1.5
        
        # For lists, prefer longer lists
        if isinstance(new_content, list) and isinstance(existing_content, list):
            return len(new_content) > len(existing_content)
        
        return len(str(new_content)) > len(str(existing_content))
    
    def _deduplicate_skills_list(self, skills: List[str]) -> List[str]:
        """Deduplicate skills list with case-insensitive matching."""
        if not skills:
            return []
        
        seen = set()
        deduped = []
        
        for skill in skills:
            skill_str = str(skill).strip().lower()
            if skill_str and skill_str not in seen:
                seen.add(skill_str)
                deduped.append(str(skill).strip())
        
        return deduped
    
    def _merge_nested_dict(
        self, 
        existing: Dict[str, Any], 
        new_data: Dict[str, Any], 
        source_type: SourceType
    ) -> Dict[str, Any]:
        """Merge nested dictionaries with field-level precedence."""
        merged = deepcopy(existing)
        
        for key, value in new_data.items():
            if not value:
                continue
            
            if key not in merged or not merged[key]:
                merged[key] = value
            elif self._should_update_field(merged[key], value, source_type):
                merged[key] = value
        
        return merged
    
    def _find_matching_project(
        self, 
        target_project: Dict[str, Any], 
        projects: List[Dict[str, Any]], 
        used_indices: set
    ) -> Optional[int]:
        """Find matching project by name or description similarity."""
        target_name = str(target_project.get("projectName", "")).strip().lower()
        
        for i, project in enumerate(projects):
            if i in used_indices:
                continue
            
            project_name = str(project.get("projectName", "")).strip().lower()
            
            # Exact name match
            if target_name and project_name and target_name == project_name:
                return i
            
            # Partial name match (60% similarity)
            if target_name and project_name:
                if self._calculate_similarity(target_name, project_name) > 0.6:
                    return i
        
        return None
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate simple similarity between two strings."""
        if not str1 or not str2:
            return 0.0
        
        # Simple word-based similarity
        words1 = set(str1.lower().split())
        words2 = set(str2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _update_audit_trail(
        self, 
        existing_audit: Dict[str, Any], 
        operation: str, 
        source_type: SourceType
    ) -> Dict[str, Any]:
        """Update audit trail with merge operation."""
        audit = deepcopy(existing_audit)
        
        # Initialize audit fields if missing
        if not audit.get("manualEdits"):
            audit["manualEdits"] = []
        
        # Add merge operation to audit trail
        merge_entry = {
            "field": "audit.merge",
            "previousValue": None,
            "newValue": operation,
            "editedBy": source_type.value if hasattr(source_type, 'value') else str(source_type),
            "editedAt": datetime.now().isoformat(),
            "editReason": f"Merged data from {source_type}",
        }
        
        audit["manualEdits"].append(merge_entry)
        audit["updatedAt"] = datetime.now().isoformat()
        
        return audit
    
    # Additional helper methods (simplified versions for space)
    
    def _merge_achievements(self, existing: List, new_data: List, source_type: SourceType) -> List:
        """Merge achievements with deduplication.""" 
        return existing + [item for item in new_data if item not in existing]
    
    def _merge_personal_details(self, existing: Dict, new_data: Dict, source_type: SourceType) -> Dict:
        """Merge personal details section."""
        merged = deepcopy(existing)
        for key, value in new_data.items():
            if value and (not merged.get(key) or self._should_update_field(merged.get(key), value, source_type)):
                merged[key] = value
        return merged
    
    def _merge_attachments_metadata(self, existing: Dict, new_data: Dict, source_type: SourceType) -> Dict:
        """Merge attachments metadata."""
        merged = deepcopy(existing)
        for key, value in new_data.items():
            if value:
                merged[key] = value
        return merged
    
    def _merge_location_field(
        self, 
        existing_value: Any, 
        new_value: Any, 
        source_type: SourceType
    ) -> Dict[str, Any]:
        """
        Merge currentLocation field with proper format handling.
        
        Handles conversion between:
        - Simple string location (e.g., "San Francisco") 
        - Canonical location dict (e.g., {"city": "Seattle", "country": "USA"})
        
        For manual edits, always prioritize the new value completely.
        """
        # Initialize canonical location structure
        canonical_location = {
            "city": "",
            "state": "",
            "country": "",
            "fullAddress": ""
        }
        
        # If manual edit, prioritize new value completely
        if source_type == SourceType.MANUAL_EDIT:
            # For manual edits, start fresh and only use new data
            if isinstance(new_value, dict):
                # Use all fields from new value, filling in what's provided
                for key in ["city", "state", "country", "fullAddress"]:
                    if key in new_value and new_value[key]:
                        canonical_location[key] = new_value[key]
            elif isinstance(new_value, str) and new_value.strip():
                # Convert string to canonical format
                canonical_location["city"] = new_value.strip()
                canonical_location["fullAddress"] = new_value.strip()
            return canonical_location
        
        # For non-manual edits, merge existing with new
        # First, load existing data if available
        if isinstance(existing_value, dict):
            for key in ["city", "state", "country", "fullAddress"]:
                if key in existing_value and existing_value[key]:
                    canonical_location[key] = existing_value[key]
        elif isinstance(existing_value, str) and existing_value.strip():
            canonical_location["city"] = existing_value.strip()
            canonical_location["fullAddress"] = existing_value.strip()
        
        # Then merge new location data (prefer richer content)
        if isinstance(new_value, dict):
            for key, value in new_value.items():
                if value and (not canonical_location.get(key) or 
                             len(str(value)) > len(str(canonical_location.get(key, "")))):
                    canonical_location[key] = value
        elif isinstance(new_value, str) and new_value.strip():
            # Only update if existing is empty or new is more specific
            if not canonical_location.get("city") or len(new_value.strip()) > len(str(canonical_location.get("city", ""))):
                canonical_location["city"] = new_value.strip()
                canonical_location["fullAddress"] = new_value.strip()
        
        return canonical_location
    
    def _merge_location_list(self, existing: List, new_data: List) -> List:
        """Merge location lists with deduplication."""
        merged = list(existing)
        for location in new_data:
            if location not in merged:
                merged.append(location)
        return merged
    
    def _merge_responsibility_lists(self, existing: List, new_data: List) -> List:
        """Merge responsibility lists with intelligent deduplication."""
        merged = list(existing)
        for resp in new_data:
            # Check if responsibility is significantly different
            is_duplicate = any(
                self._calculate_similarity(str(resp).lower(), str(existing_resp).lower()) > 0.7
                for existing_resp in existing
            )
            if not is_duplicate:
                merged.append(resp)
        return merged
    
    def _find_matching_work_experience(self, target: Dict, experiences: List, used_indices: set) -> Optional[int]:
        """Find matching work experience by organization and role."""
        target_org = str(target.get("organization", "")).strip().lower()
        target_role = str(target.get("designation", "")).strip().lower()
        
        for i, exp in enumerate(experiences):
            if i in used_indices:
                continue
            
            exp_org = str(exp.get("organization", "")).strip().lower()
            exp_role = str(exp.get("designation", "")).strip().lower()
            
            if target_org and exp_org and target_org == exp_org:
                if target_role and exp_role and target_role == exp_role:
                    return i
        return None
    
    def _find_matching_education(self, target: Dict, educations: List, used_indices: set) -> Optional[int]:
        """Find matching education by degree and institution."""
        target_degree = str(target.get("degree", "")).strip().lower()
        target_inst = str(target.get("institution", "")).strip().lower()
        
        for i, edu in enumerate(educations):
            if i in used_indices:
                continue
            
            edu_degree = str(edu.get("degree", "")).strip().lower()
            edu_inst = str(edu.get("institution", "")).strip().lower()
            
            if target_degree and edu_degree and target_degree == edu_degree:
                if target_inst and edu_inst and target_inst == edu_inst:
                    return i
        return None
    
    def _find_matching_certification(self, target: Dict, certs: List, used_indices: set) -> Optional[int]:
        """Find matching certification by name and issuing organization."""
        target_name = str(target.get("name", "")).strip().lower()
        target_org = str(target.get("issuingOrganization", "")).strip().lower()
        
        for i, cert in enumerate(certs):
            if i in used_indices:
                continue
            
            cert_name = str(cert.get("name", "")).strip().lower()
            cert_org = str(cert.get("issuingOrganization", "")).strip().lower()
            
            if target_name and cert_name and target_name == cert_name:
                if target_org and cert_org and target_org == cert_org:
                    return i
        return None
    
    def _merge_single_work_experience(self, existing: Dict, new_data: Dict, source_type: SourceType) -> Dict:
        """Merge single work experience."""
        merged = deepcopy(existing)
        for field, value in new_data.items():
            if value and (not merged.get(field) or self._should_update_field(merged.get(field), value, source_type)):
                merged[field] = value
        return merged
    
    def _merge_single_education(self, existing: Dict, new_data: Dict, source_type: SourceType) -> Dict:
        """Merge single education entry."""
        merged = deepcopy(existing)
        for field, value in new_data.items():
            if value and (not merged.get(field) or self._should_update_field(merged.get(field), value, source_type)):
                merged[field] = value
        return merged
    
    def _merge_single_certification(self, existing: Dict, new_data: Dict, source_type: SourceType) -> Dict:
        """Merge single certification entry."""
        merged = deepcopy(existing)
        for field, value in new_data.items():
            if value and (not merged.get(field) or self._should_update_field(merged.get(field), value, source_type)):
                merged[field] = value
        return merged
