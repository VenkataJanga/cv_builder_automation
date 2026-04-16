"""
Legacy CV Merge Service

Provides backward compatibility with the existing session-based CV merge logic
while integrating with the new Canonical CV Schema services.

This service bridges the gap between the legacy session format and the new
schema-based approach.
"""

from typing import Dict, Any
from .schema_merge_service import SchemaMergeService
from .schema_mapper_service import SchemaMapperService
from .schema_validation_service import SchemaValidationService
from ..enums import SourceType


class MergeCVService:
    """
    Legacy merge service that integrates with Canonical CV Schema.
    
    This service provides backward compatibility for existing session-based
    CV merge operations while ensuring consistency with the new schema.
    
    Rules:
    - Uses Canonical CV Schema as the underlying data model
    - Existing manually answered values win (source precedence)
    - Missing fields are filled from parsed data
    - All data is validated and properly structured
    """

    def __init__(self):
        self.schema_merge_service = SchemaMergeService()
        self.schema_mapper_service = SchemaMapperService()
        self.validation_service = SchemaValidationService()

    def merge(self, existing: dict, parsed: dict, source_type: str = "unknown") -> dict:
        """
        Merge parsed data into existing session CV data.
        
        Args:
            existing: Existing CV data from session
            parsed: Newly parsed/extracted CV data
            source_type: Source of the parsed data (for precedence rules)
            
        Returns:
            Merged CV data following Canonical CV Schema
        """
        try:
            # Convert source_type to enum
            if source_type in ["audio_upload", "audio_recording", "start_recording"]:
                source = SourceType.AUDIO_UPLOAD
            elif source_type in ["bot_conversation", "chat", "conversation"]:
                source = SourceType.BOT_CONVERSATION
            elif source_type in ["docx_upload", "pdf_upload", "document_upload"]:
                source = SourceType.DOCUMENT_UPLOAD
            elif source_type in ["manual_edit", "manual_entry", "user_edit"]:
                source = SourceType.MANUAL_EDIT
            else:
                source = SourceType.MANUAL_ENTRY  # Default for backward compatibility
            
            # Convert legacy data to canonical schema
            existing_canonical = self._convert_to_canonical_schema(existing)
            parsed_canonical = self._convert_to_canonical_schema(parsed)
            
            # Use the new merge service for proper merging
            merged_canonical = self.schema_merge_service.merge_canonical_cvs(
                existing_cv=existing_canonical,
                new_data=parsed_canonical,
                source_type=source,
                operation="session_merge"
            )
            
            # Validate the merged result
            validation_result = self.validation_service.validate_for_save(merged_canonical)
            
            # Convert back to legacy session format for backward compatibility
            legacy_format = self._convert_to_legacy_format(merged_canonical)
            
            # Add validation metadata to session data
            legacy_format["_schema_validation"] = validation_result.to_dict()
            legacy_format["_canonical_schema_version"] = "1.1"
            
            return legacy_format
            
        except Exception as e:
            # Fallback to legacy merge if something goes wrong
            return self._legacy_merge_fallback(existing, parsed)

    def _convert_to_canonical_schema(self, data: dict) -> dict:
        """Convert legacy session data to Canonical CV Schema format."""
        if not data:
            return self._get_empty_canonical_schema()
        
        # Check if it's already in canonical format
        if "candidate" in data and "skills" in data and "experience" in data:
            return data
        
        # For simple data with just a few fields (like manual edits), 
        # use direct conversion to avoid schema mapper overwriting with empty values
        if len(data) <= 5 and not any(k in data for k in ["projects", "work_history", "education"]):
            return self._convert_legacy_to_basic_canonical(data)
        
        # Use schema mapper for complex data
        try:
            return self.schema_mapper_service.map_to_canonical(
                source_data=data, 
                source_type=SourceType.MANUAL_ENTRY.value
            )
        except Exception:
            # If mapping fails, create basic canonical structure
            return self._convert_legacy_to_basic_canonical(data)

    def _convert_to_legacy_format(self, canonical_data: dict) -> dict:
        """Convert canonical schema back to legacy session format."""
        legacy_data = {}
        
        # Extract candidate info
        if "candidate" in canonical_data:
            candidate = canonical_data["candidate"]
            # Handle location - convert canonical structure to legacy format
            location = candidate.get("currentLocation", {})
            
            # Filter out empty canonical locations
            if isinstance(location, dict):
                # Check if all location fields are empty
                has_data = any(location.get(key, "").strip() for key in ["city", "state", "country", "fullAddress"])
                if not has_data:
                    location = {}
            else:
                location = {}
            
            legacy_data.update({
                "name": candidate.get("fullName", ""),
                "first_name": candidate.get("firstName", ""),
                "last_name": candidate.get("lastName", ""),
                "phone": candidate.get("phoneNumber", ""),
                "email": candidate.get("email", ""),
                "location": location,
                "summary": candidate.get("summary", ""),
                "experience_years": candidate.get("totalExperienceYears", 0),
                "current_organization": candidate.get("currentOrganization", ""),
                "current_designation": candidate.get("currentDesignation", ""),
                "current_ctc": candidate.get("currentCTC", ""),
                "expected_ctc": candidate.get("expectedCTC", ""),
                "notice_period": candidate.get("noticePeriod", "")
            })

        # Extract skills
        if "skills" in canonical_data:
            skills = canonical_data["skills"]
            legacy_data["skills"] = skills

        # Extract experience
        if "experience" in canonical_data:
            experience = canonical_data["experience"]
            legacy_data.update({
                "work_history": experience.get("workHistory", []),
                "projects": experience.get("projects", []),
                "domain_experience": experience.get("domainExperience", [])
            })

        # Extract education
        if "education" in canonical_data:
            legacy_data["education"] = canonical_data["education"]

        # Extract certifications
        if "certifications" in canonical_data:
            legacy_data["certifications"] = canonical_data["certifications"]

        return legacy_data

    def _convert_legacy_to_basic_canonical(self, legacy_data: dict) -> dict:
        """Convert legacy data to basic canonical structure."""
        canonical = self._get_empty_canonical_schema()
        
        # Map basic fields
        if "name" in legacy_data:
            canonical["candidate"]["fullName"] = legacy_data["name"]
        if "first_name" in legacy_data:
            canonical["candidate"]["firstName"] = legacy_data["first_name"]
        if "last_name" in legacy_data:
            canonical["candidate"]["lastName"] = legacy_data["last_name"]
        if "phone" in legacy_data:
            canonical["candidate"]["phoneNumber"] = legacy_data["phone"]
        if "email" in legacy_data:
            canonical["candidate"]["email"] = legacy_data["email"]
        
        # Handle location - convert string to canonical format if needed
        if "location" in legacy_data:
            location_data = legacy_data["location"]
            if isinstance(location_data, str) and location_data.strip():
                # Convert string location to canonical structure
                canonical["candidate"]["currentLocation"] = {
                    "city": location_data.strip(),
                    "state": "",
                    "country": "",
                    "fullAddress": location_data.strip()
                }
            elif isinstance(location_data, dict) and location_data:
                # Already in dict format, ensure all required keys exist
                canonical["candidate"]["currentLocation"] = {
                    "city": location_data.get("city", ""),
                    "state": location_data.get("state", ""),
                    "country": location_data.get("country", ""),
                    "fullAddress": location_data.get("fullAddress", location_data.get("city", ""))
                }
            else:
                # Empty or None
                canonical["candidate"]["currentLocation"] = {}
        
        if "summary" in legacy_data:
            canonical["candidate"]["summary"] = legacy_data["summary"]

        # Map skills
        if "skills" in legacy_data:
            if isinstance(legacy_data["skills"], dict):
                canonical["skills"] = legacy_data["skills"]
            elif isinstance(legacy_data["skills"], list):
                canonical["skills"]["primarySkills"] = legacy_data["skills"]

        # Map experience
        if "work_history" in legacy_data:
            canonical["experience"]["workHistory"] = legacy_data["work_history"]
        if "projects" in legacy_data:
            canonical["experience"]["projects"] = legacy_data["projects"]

        # Map education
        if "education" in legacy_data:
            canonical["education"] = legacy_data["education"]

        return canonical

    def _get_empty_canonical_schema(self) -> dict:
        """Get empty canonical schema structure."""
        return {
            "cvId": "",
            "sourceType": SourceType.MANUAL_ENTRY.value,
            "candidate": {
                "fullName": "",
                "firstName": "",
                "lastName": "",
                "phoneNumber": "",
                "email": "",
                "currentLocation": {},
                "summary": "",
                "totalExperienceYears": 0,
                "currentOrganization": "",
                "currentDesignation": ""
            },
            "skills": {
                "primarySkills": [],
                "technicalSkills": [],
                "toolsAndPlatforms": []
            },
            "experience": {
                "workHistory": [],
                "projects": []
            },
            "education": [],
            "certifications": [],
            "audit": {
                "createdAt": "",
                "updatedAt": "",
                "manualEdits": []
            }
        }

    def _legacy_merge_fallback(self, existing: dict, parsed: dict) -> dict:
        """Fallback to simple legacy merge if schema-based merge fails."""
        result = existing.copy()
        
        for key, value in parsed.items():
            if isinstance(value, dict) and key in result and isinstance(result[key], dict):
                # Merge dictionaries recursively
                for sub_key, sub_value in value.items():
                    if not result[key].get(sub_key):
                        result[key][sub_key] = sub_value
            elif isinstance(value, list) and key in result and isinstance(result[key], list):
                # Merge lists with deduplication
                for item in value:
                    if item not in result[key]:
                        result[key].append(item)
            elif not result.get(key):
                # Add new fields
                result[key] = value
                
        return result
