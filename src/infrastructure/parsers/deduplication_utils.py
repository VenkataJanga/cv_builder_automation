"""
Deduplication utilities for CV data to remove duplicate entries.
"""
from typing import List, Dict, Any
import hashlib
import json


def deduplicate_list_by_keys(items: List[Dict[str, Any]], unique_keys: List[str]) -> List[Dict[str, Any]]:
    """
    Deduplicate a list of dictionaries based on specified unique keys.
    
    Args:
        items: List of dictionaries to deduplicate
        unique_keys: List of keys to use for uniqueness check
        
    Returns:
        Deduplicated list
    """
    if not items:
        return []
    
    seen = set()
    deduplicated = []
    
    for item in items:
        # Create a hash from the unique keys
        key_values = tuple(str(item.get(key, '')).strip().lower() for key in unique_keys)
        
        if key_values not in seen and any(key_values):  # Only add if not all empty
            seen.add(key_values)
            deduplicated.append(item)
    
    return deduplicated


def deduplicate_projects(projects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicate project experience entries.
    
    Args:
        projects: List of project dictionaries
        
    Returns:
        Deduplicated list of projects
    """
    return deduplicate_list_by_keys(projects, ['project_name', 'client', 'role'])


def deduplicate_experience(experience: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicate work experience entries.
    
    Args:
        experience: List of experience dictionaries
        
    Returns:
        Deduplicated list of experience
    """
    return deduplicate_list_by_keys(experience, ['company_name', 'designation', 'start_date'])


def deduplicate_education(education: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicate education entries.
    
    Args:
        education: List of education dictionaries
        
    Returns:
        Deduplicated list of education
    """
    return deduplicate_list_by_keys(education, ['degree', 'institution', 'graduation_year'])


def deduplicate_certifications(certifications: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicate certification entries.
    
    Args:
        certifications: List of certification dictionaries
        
    Returns:
        Deduplicated list of certifications
    """
    return deduplicate_list_by_keys(certifications, ['name', 'issuing_organization', 'issue_date'])


def deduplicate_skills(skills: List[str]) -> List[str]:
    """
    Deduplicate skills list while preserving order.
    
    Args:
        skills: List of skill strings
        
    Returns:
        Deduplicated list of skills
    """
    if not skills:
        return []
    
    seen = set()
    deduplicated = []
    
    for skill in skills:
        # Handle both string and dict formats
        if isinstance(skill, dict):
            # For dict format (single-key objects), create signature from key-value pair
            for key, value in skill.items():
                signature = f"{key}:{str(value).strip().lower()}"
                if signature not in seen:
                    seen.add(signature)
                    deduplicated.append(skill)
                break  # Only process first key-value pair
        elif isinstance(skill, str):
            # For string format
            skill_normalized = skill.strip().lower()
            if skill_normalized and skill_normalized not in seen:
                seen.add(skill_normalized)
                deduplicated.append(skill.strip())
    
    return deduplicated


def deduplicate_cv_data(cv_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deduplicate all sections in CV data.
    
    Args:
        cv_data: Complete CV data dictionary
        
    Returns:
        CV data with all duplicates removed
    """
    deduplicated = cv_data.copy()
    
    # Deduplicate project_experience
    if 'project_experience' in deduplicated and isinstance(deduplicated['project_experience'], list):
        original_count = len(deduplicated['project_experience'])
        deduplicated['project_experience'] = deduplicate_projects(deduplicated['project_experience'])
        new_count = len(deduplicated['project_experience'])
        if original_count != new_count:
            print(f"[DEDUP] Projects: {original_count} → {new_count} (removed {original_count - new_count} duplicates)")
    
    # Deduplicate experience
    if 'experience' in deduplicated and isinstance(deduplicated['experience'], list):
        original_count = len(deduplicated['experience'])
        deduplicated['experience'] = deduplicate_experience(deduplicated['experience'])
        new_count = len(deduplicated['experience'])
        if original_count != new_count:
            print(f"[DEDUP] Experience: {original_count} → {new_count} (removed {original_count - new_count} duplicates)")
    
    # Deduplicate education
    if 'education' in deduplicated and isinstance(deduplicated['education'], list):
        original_count = len(deduplicated['education'])
        deduplicated['education'] = deduplicate_education(deduplicated['education'])
        new_count = len(deduplicated['education'])
        if original_count != new_count:
            print(f"[DEDUP] Education: {original_count} → {new_count} (removed {original_count - new_count} duplicates)")
    
    # Deduplicate certifications
    if 'certifications' in deduplicated and isinstance(deduplicated['certifications'], list):
        original_count = len(deduplicated['certifications'])
        deduplicated['certifications'] = deduplicate_certifications(deduplicated['certifications'])
        new_count = len(deduplicated['certifications'])
        if original_count != new_count:
            print(f"[DEDUP] Certifications: {original_count} → {new_count} (removed {original_count - new_count} duplicates)")
    
    # Deduplicate skills - handle new array of objects format
    if 'skills' in deduplicated and isinstance(deduplicated['skills'], dict):
        if 'technical_skills' in deduplicated['skills']:
            tech_skills = deduplicated['skills']['technical_skills']
            
            # Handle array of single-key objects format
            if isinstance(tech_skills, list):
                original_count = len(tech_skills)
                deduplicated['skills']['technical_skills'] = deduplicate_skills(tech_skills)
                new_count = len(deduplicated['skills']['technical_skills'])
                if original_count != new_count:
                    print(f"[DEDUP] Technical Skills: {original_count} → {new_count} (removed {original_count - new_count} duplicates)")
            # Handle old dict format for backward compatibility
            elif isinstance(tech_skills, dict):
                # Old format - just ensure no empty categories
                cleaned_tech_skills = {k: v for k, v in tech_skills.items() if v and str(v).strip()}
                deduplicated['skills']['technical_skills'] = cleaned_tech_skills
        
        if 'soft_skills' in deduplicated['skills'] and isinstance(deduplicated['skills']['soft_skills'], list):
            original_count = len(deduplicated['skills']['soft_skills'])
            deduplicated['skills']['soft_skills'] = deduplicate_skills(deduplicated['skills']['soft_skills'])
            new_count = len(deduplicated['skills']['soft_skills'])
            if original_count != new_count:
                print(f"[DEDUP] Soft Skills: {original_count} → {new_count} (removed {original_count - new_count} duplicates)")
    
    # Deduplicate languages
    if 'languages' in deduplicated and isinstance(deduplicated['languages'], list):
        original_count = len(deduplicated['languages'])
        deduplicated['languages'] = deduplicate_skills(deduplicated['languages'])
        new_count = len(deduplicated['languages'])
        if original_count != new_count:
            print(f"[DEDUP] Languages: {original_count} → {new_count} (removed {original_count - new_count} duplicates)")
    
    return deduplicated
