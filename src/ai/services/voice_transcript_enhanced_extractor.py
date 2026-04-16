"""
Enhanced Voice Transcript Extractor for CV Builder
Addresses gaps in extraction: secondary skills, operating systems, AI frameworks, databases, all projects, education
"""

import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ExtractionPattern:
    """Pattern configuration for extracting specific information"""
    field_name: str
    keywords: List[str]
    stop_keywords: List[str]
    pattern_type: str  # 'list', 'single', 'structured'


class VoiceTranscriptEnhancedExtractor:
    """
    Enhanced extractor for voice transcripts with improved field coverage
    Addresses missing fields: secondary skills, OS, AI frameworks, databases, projects, education
    """
    
    def __init__(self):
        self.extraction_patterns = self._initialize_patterns()
        
    def _initialize_patterns(self) -> Dict[str, ExtractionPattern]:
        """Initialize extraction patterns for all CV fields"""
        return {
            'primary_skills': ExtractionPattern(
                field_name='primary_skills',
                keywords=['primary skill', 'primary skills', 'main skill', 'core skill'],
                stop_keywords=['secondary', 'additional', 'my secondary', 'coming to'],
                pattern_type='list'
            ),
            'secondary_skills': ExtractionPattern(
                field_name='secondary_skills',
                keywords=['secondary skill', 'secondary skills', 'additional skill', 'also includes'],
                stop_keywords=['hands-on', 'experience with', 'operating system', 'on the database'],
                pattern_type='list'
            ),
            'ai_frameworks': ExtractionPattern(
                field_name='ai_frameworks',
                keywords=['ai framework', 'ai frameworks', 'hands-on experience with'],
                stop_keywords=['operating system', 'well-versed', 'on the database'],
                pattern_type='list'
            ),
            'operating_systems': ExtractionPattern(
                field_name='operating_systems',
                keywords=['operating system', 'linux', 'windows', 'well-versed in working with'],
                stop_keywords=['database', 'on the database side'],
                pattern_type='list'
            ),
            'databases': ExtractionPattern(
                field_name='databases',
                keywords=['database', 'on the database side', 'database experience'],
                stop_keywords=['over the course', 'my career', 'domains', 'current role'],
                pattern_type='list'
            ),
            'domains': ExtractionPattern(
                field_name='domains',
                keywords=['domains', 'domain', 'worked across'],
                stop_keywords=['current role', 'my current role'],
                pattern_type='list'
            ),
            'education': ExtractionPattern(
                field_name='education',
                keywords=['education', 'educational', 'master of', 'bachelor of', 'intermediate', '10th standard', '12th standard'],
                stop_keywords=['thank you', 'that\'s all'],
                pattern_type='structured'
            )
        }
    
    def extract_comprehensive(self, transcript: str) -> Dict[str, Any]:
        """
        Extract comprehensive CV data from voice transcript
        
        Args:
            transcript: Raw or normalized voice transcript
            
        Returns:
            Complete CV data dictionary with all fields
        """
        # Normalize transcript
        normalized = self._normalize_transcript(transcript)
        
        # Extract all sections
        cv_data = {
            'header': self._extract_header(normalized),
            'summary': self._extract_professional_summary(normalized),
            'skills': self._extract_primary_skills(normalized),
            'secondary_skills': self._extract_secondary_skills(normalized),
            'tools_and_platforms': self._extract_tools_and_platforms(normalized),
            'ai_frameworks': self._extract_ai_frameworks(normalized),
            'cloud_platforms': self._extract_cloud_platforms(normalized),
            'operating_systems': self._extract_operating_systems(normalized),
            'databases': self._extract_databases(normalized),
            'domain_expertise': self._extract_domain_expertise(normalized),
            'employment': self._extract_employment(normalized),
            'work_experience': self._extract_work_experience(normalized),
            'project_experience': self._extract_all_projects(normalized),
            'certifications': self._extract_certifications(normalized),
            'education': self._extract_education(normalized),
            'publications': [],
            'awards': [],
            'languages': [],
            'schema_version': '1.0'
        }
        
        return cv_data
    
    def _normalize_transcript(self, transcript: str) -> str:
        """Normalize transcript for easier extraction"""
        # Convert to lowercase for pattern matching
        normalized = transcript.lower()
        
        # Fix common speech-to-text errors
        corrections = {
            'at the rate': '@',
            'langraph': 'langgraph',
            'langraph': 'langgraph',
            'langroth': 'langgraph',
            'crue ai': 'crew ai',
            'autogen': 'autogen',
            'autozen': 'autogen',
            'common sprint': 'commonspirit',
            'daimler truck': 'daimlertruck',
            'portrait id': 'portal id',
            'percentile': 'percentage',
            'sensational': 'seasonal',
            'transport formations': 'transformations',
            'ato layer': 'dto layer',
            'intelligency': 'intelligence'
        }
        
        for error, correction in corrections.items():
            normalized = normalized.replace(error, correction)
        
        return normalized
    
    def _extract_header(self, transcript: str) -> Dict[str, Any]:
        """Extract header information: name, contact, employee ID, grade, location"""
        header = {
            'full_name': '',
            'current_title': '',
            'location': '',
            'current_organization': '',
            'total_experience': '',
            'target_role': None,
            'email': '',
            'employee_id': '',
            'contact_number': '',
            'grade': ''
        }
        
        # Extract name
        name_match = re.search(r'my name is ([a-z\s]+?)(?:\.|,|my)', transcript)
        if name_match:
            header['full_name'] = name_match.group(1).strip().title()
        
        # Extract portal/employee ID
        id_patterns = [
            r'portal id is ([a-z0-9]+)',
            r'employee id is ([a-z0-9]+)',
            r'id is ([a-z0-9]+)'
        ]
        for pattern in id_patterns:
            id_match = re.search(pattern, transcript)
            if id_match:
                header['employee_id'] = id_match.group(1)
                break
        
        # Extract grade
        grade_match = re.search(r'grade is (\d+)', transcript)
        if grade_match:
            header['grade'] = grade_match.group(1)
        
        # Extract contact number
        phone_patterns = [
            r'reach (?:at |it at )?(\d{3}[-\s]?\d{3}[-\s]?\d{4})',
            r'contact (?:number |is )?(\d{3}[-\s]?\d{3}[-\s]?\d{4})',
            r'phone (?:number |is )?(\d{3}[-\s]?\d{3}[-\s]?\d{4})'
        ]
        for pattern in phone_patterns:
            phone_match = re.search(pattern, transcript)
            if phone_match:
                header['contact_number'] = phone_match.group(1).replace('-', '').replace(' ', '')
                break
        
        # Extract email
        email_patterns = [
            r'email (?:address )?is ([a-z0-9.]+)@([a-z0-9.]+)',
            r'email (?:address )?is ([a-z0-9.]+)\s+@\s+([a-z0-9.]+)'
        ]
        for pattern in email_patterns:
            email_match = re.search(pattern, transcript)
            if email_match:
                header['email'] = f"{email_match.group(1)}@{email_match.group(2)}"
                break
        
        # Extract experience
        exp_match = re.search(r'(?:over |have )?(\d+)\s*(?:\+)?\s*years of experience', transcript)
        if exp_match:
            header['total_experience'] = f"{exp_match.group(1)} years"
        
        # Extract current role and organization
        role_match = re.search(r'current role is ([^,\.]+)', transcript)
        if role_match:
            header['current_title'] = role_match.group(1).strip().title()
        
        org_match = re.search(r'(?:at |with )([a-z\s]+?)(?:,\s*based|based)', transcript)
        if org_match:
            header['current_organization'] = org_match.group(1).strip().upper()
        
        # Extract location
        location_match = re.search(r'based (?:on |in )?the ([a-z]+)', transcript)
        if location_match:
            header['location'] = location_match.group(1).strip().title()
        
        return header
    
    def _extract_professional_summary(self, transcript: str) -> str:
        """Extract professional summary"""
        summary_match = re.search(
            r'professional summary[,\s]+(.+?)(?:coming to|my skill|skillset)',
            transcript,
            re.DOTALL
        )
        
        if summary_match:
            summary = summary_match.group(1).strip()
            # Clean up and format
            summary = ' '.join(summary.split())
            return summary[:500]  # Limit length
        
        return ''
    
    def _extract_primary_skills(self, transcript: str) -> List[str]:
        """Extract primary skills"""
        skills = []
        
        # Find primary skills section
        primary_match = re.search(
            r'primary skill(?:s)? is ([^\.]+?)(?:\.|my secondary|secondary skill)',
            transcript
        )
        
        if primary_match:
            skills_text = primary_match.group(1)
            skills = self._parse_skill_list(skills_text)
        
        return skills
    
    def _extract_secondary_skills(self, transcript: str) -> List[str]:
        """Extract secondary skills"""
        skills = []
        
        # Find secondary skills section
        secondary_patterns = [
            r'secondary skill(?:s)? (?:includes? )?([^\.]+?)(?:\.|i have|hands-on)',
            r'also (?:have |includes )([^\.]+?)(?:\.|i have|hands-on)'
        ]
        
        for pattern in secondary_patterns:
            match = re.search(pattern, transcript)
            if match:
                skills_text = match.group(1)
                skills = self._parse_skill_list(skills_text)
                break
        
        return skills
    
    def _extract_ai_frameworks(self, transcript: str) -> List[str]:
        """Extract AI frameworks"""
        frameworks = []
        
        # Find AI frameworks section
        ai_match = re.search(
            r'(?:ai framework(?:s)?|hands-on experience with)(?:\s+such as)?\s+([^\.]+?)(?:\.|i am|well-versed)',
            transcript
        )
        
        if ai_match:
            frameworks_text = ai_match.group(1)
            frameworks = self._parse_skill_list(frameworks_text)
        
        return frameworks
    
    def _extract_operating_systems(self, transcript: str) -> List[str]:
        """Extract operating systems"""
        os_list = []
        
        # Find OS section
        os_match = re.search(
            r'(?:operating system(?:s)?|well-versed in working with)\s+([^\.]+?)(?:\.|on the database)',
            transcript
        )
        
        if os_match:
            os_text = os_match.group(1)
            os_list = self._parse_skill_list(os_text)
        
        return os_list
    
    def _extract_databases(self, transcript: str) -> List[str]:
        """Extract databases"""
        databases = []
        
        # Find database section
        db_patterns = [
            r'on the database side[,\s]+(?:i have )?(?:strong )?(?:experience|expertise) with ([^\.]+?)(?:\.|over the course)',
            r'database(?:s)? (?:include|are) ([^\.]+?)(?:\.|over the course)'
        ]
        
        for pattern in db_patterns:
            match = re.search(pattern, transcript)
            if match:
                db_text = match.group(1)
                databases = self._parse_skill_list(db_text)
                break
        
        return databases
    
    def _extract_cloud_platforms(self, transcript: str) -> List[str]:
        """Extract cloud platforms"""
        clouds = []
        
        cloud_keywords = ['aws', 'azure', 'gcp', 'google cloud']
        for keyword in cloud_keywords:
            if keyword in transcript:
                clouds.append(keyword.upper() if keyword in ['aws', 'gcp'] else keyword.title())
        
        return list(set(clouds))
    
    def _extract_tools_and_platforms(self, transcript: str) -> List[str]:
        """Extract tools and platforms"""
        tools = []
        
        # Common tools to look for
        tool_keywords = ['jenkins', 'docker', 'kubernetes', 'git', 'adf', 'adls', 'databricks', 'pyspark']
        
        for keyword in tool_keywords:
            if keyword in transcript:
                tools.append(keyword.title())
        
        return list(set(tools))
    
    def _extract_domain_expertise(self, transcript: str) -> List[str]:
        """Extract domain expertise"""
        domains = []
        
        # Find domains section
        domain_match = re.search(
            r'(?:worked across|domains)(?:\s+including)?\s+([^\.]+?)(?:\.|my current role)',
            transcript
        )
        
        if domain_match:
            domain_text = domain_match.group(1)
            # Clean and split
            domain_text = domain_text.replace(' and ', ',')
            domains = [d.strip().title() for d in domain_text.split(',') if d.strip()]
        
        return domains
    
    def _extract_employment(self, transcript: str) -> Dict[str, Any]:
        """Extract employment information"""
        employment = {
            'current_company': '',
            'years_with_current_company': 0,
            'clients': []
        }
        
        # Extract current company
        org_match = re.search(r'(?:at |with )([a-z\s]+?)(?:,\s*based|based)', transcript)
        if org_match:
            employment['current_company'] = org_match.group(1).strip().upper()
        
        # Extract years with company
        years_match = re.search(r'(?:with the organization|with them) for (?:the )?(?:past |first )?(\d+) years?', transcript)
        if years_match:
            employment['years_with_current_company'] = int(years_match.group(1))
        
        # Extract clients
        clients_match = re.search(r'(?:clients|worked with clients) (?:such as |like )?([^\.]+?)(?:\.|now coming)', transcript)
        if clients_match:
            clients_text = clients_match.group(1)
            clients_text = clients_text.replace(' and ', ',')
            employment['clients'] = [c.strip().title() for c in clients_text.split(',') if c.strip()]
        
        return employment
    
    def _extract_work_experience(self, transcript: str) -> List[Dict[str, Any]]:
        """Extract work experience (if different from projects)"""
        # In voice transcripts, work experience is usually covered in projects
        return []
    
    def _extract_all_projects(self, transcript: str) -> List[Dict[str, Any]]:
        """Extract ALL project experiences"""
        projects = []
        
        # Find all project mentions
        # Pattern 1: "project one", "my project one", "first project"
        # Pattern 2: "project name is", "my project", "second project"
        
        # Split transcript into project sections
        project_sections = self._split_into_project_sections(transcript)
        
        for section in project_sections:
            project = self._parse_project_section(section)
            if project and project.get('project_name'):
                projects.append(project)
        
        return projects
    
    def _split_into_project_sections(self, transcript: str) -> List[str]:
        """Split transcript into individual project sections"""
        sections = []
        
        # Find all project markers
        project_markers = [
            r'(?:my )?(?:first |second |third |project one|project two|project three|project \d+)',
            r'(?:my )?project (?:name )?is',
            r'coming to (?:my )?project'
        ]
        
        # Use regex to find all project start positions
        pattern = '|'.join(project_markers)
        matches = list(re.finditer(pattern, transcript))
        
        if not matches:
            # Try to find at least one project mention
            project_match = re.search(r'project experience(.+?)(?:education|certification|thank you)', transcript, re.DOTALL)
            if project_match:
                sections.append(project_match.group(1))
            return sections
        
        # Extract sections between markers
        for i, match in enumerate(matches):
            start = match.start()
            # Find end: next project or education section
            if i + 1 < len(matches):
                end = matches[i + 1].start()
            else:
                # Last project - ends at education or end of transcript
                edu_match = re.search(r'(?:education|certification|thank you)', transcript[start:])
                end = start + edu_match.start() if edu_match else len(transcript)
            
            sections.append(transcript[start:end])
        
        return sections
    
    def _parse_project_section(self, section: str) -> Dict[str, Any]:
        """Parse a single project section"""
        project = {
            'project_name': '',
            'client': '',
            'domain': '',
            'technologies_used': [],
            'project_description': '',
            'role': '',
            'responsibilities': []
        }
        
        # Extract project name
        name_patterns = [
            r'project (?:name )?is ([^,\.]+?)(?:\.|,|client)',
            r'(?:first |second |third )project[,\s]+(?:its name is |name is )?([^,\.]+?)(?:\.|,|client)',
            r'project one[,\s]+(?:its name is )?([^,\.]+?)(?:\.|,|client)'
        ]
        for pattern in name_patterns:
            name_match = re.search(pattern, section)
            if name_match:
                project['project_name'] = name_match.group(1).strip().title()
                break
        
        # Extract client
        client_match = re.search(r'client (?:is |name is )?([^,\.]+?)(?:\.|,|project description)', section)
        if client_match:
            project['client'] = client_match.group(1).strip().title()
        
        # Extract domain
        domain_match = re.search(r'domain (?:is )?([^,\.]+?)(?:\.|,|technolog)', section)
        if domain_match:
            project['domain'] = domain_match.group(1).strip().title()
        
        # Extract technologies
        tech_patterns = [
            r'technolog(?:ies|y) used (?:are |is )?([^\.]+?)(?:\.|project description)',
            r'using ([a-z, ]+)(?:in|and|to)',
        ]
        for pattern in tech_patterns:
            tech_match = re.search(pattern, section)
            if tech_match:
                tech_text = tech_match.group(1)
                project['technologies_used'] = self._parse_skill_list(tech_text)
                break
        
        # Extract project description
        desc_patterns = [
            r'project description (?:is )?(.+?)(?:coming to my role|role|responsibilities)',
            r'the application (?:is )?(.+?)(?:coming to my role|role|responsibilities)',
            r'description (?:is )?(.+?)(?:coming to my role|role|responsibilities)'
        ]
        for pattern in desc_patterns:
            desc_match = re.search(pattern, section, re.DOTALL)
            if desc_match:
                desc = desc_match.group(1).strip()
                project['project_description'] = ' '.join(desc.split())[:300]
                break
        
        # Extract role
        role_match = re.search(r'(?:my )?role (?:is |was )?([^,\.]+?)(?:\.|,|responsibilit)', section)
        if role_match:
            project['role'] = role_match.group(1).strip().title()
        
        # Extract responsibilities
        resp_patterns = [
            r'responsibilit(?:ies|y)[,\s]+(.+?)(?:my (?:next |second )|education|certification|project)',
            r'(?:coming to )?(?:my )?(?:roles and )?responsibilit(?:ies|y)[,\s]+(.+?)(?:my (?:next |second )|education|certification|project)'
        ]
        for pattern in resp_patterns:
            resp_match = re.search(pattern, section, re.DOTALL)
            if resp_match:
                resp_text = resp_match.group(1).strip()
                # Split by common delimiters
                responsibilities = []
                for resp in re.split(r'[,\.]\s*(?:i |and i |also i )', resp_text):
                    resp = resp.strip()
                    if resp and len(resp) > 10:
                        responsibilities.append(resp.capitalize())
                project['responsibilities'] = responsibilities[:10]  # Limit to 10
                break
        
        return project
    
    def _extract_certifications(self, transcript: str) -> List[Dict[str, Any]]:
        """Extract certifications"""
        certifications = []
        
        # Find certifications section
        cert_match = re.search(r'certification(?:s)?[,\s]+(.+?)(?:education|thank you)', transcript, re.DOTALL)
        if cert_match:
            cert_text = cert_match.group(1)
            # Parse individual certifications
            # This is a simplified version - can be enhanced
            cert_lines = cert_text.split('.')
            for line in cert_lines:
                if len(line.strip()) > 10:
                    certifications.append({
                        'certification_name': line.strip().title(),
                        'issuing_organization': '',
                        'year_obtained': ''
                    })
        
        return certifications
    
    def _extract_education(self, transcript: str) -> List[Dict[str, Any]]:
        """Extract education details - ALL qualifications"""
        education = []
        
        # Find education section
        edu_section_match = re.search(r'(?:coming to my education(?:al)?s?)[,\s]+(.+?)(?:thank you|$)', transcript, re.DOTALL)
        if not edu_section_match:
            return education
        
        edu_text = edu_section_match.group(1)
        
        # Look for each degree separately with more specific patterns
        
        # Master's degree
        master_match = re.search(r'(?:completed |have )?master(?:s)? of computer applications(.+?)(?:bachelor|intermediate|i have completed my bachelor)', edu_text, re.IGNORECASE | re.DOTALL)
        if master_match:
            edu_entry = self._parse_education_segment(f"master of computer applications {master_match.group(1)}", 'Master of Computer Applications')
            if edu_entry:
                education.append(edu_entry)
        
        # Bachelor's degree  
        bachelor_match = re.search(r'(?:completed |have )?bachelor(?:s)? of science(.+?)(?:intermediate|and intermediate|my intermediate)', edu_text, re.IGNORECASE | re.DOTALL)
        if bachelor_match:
            edu_entry = self._parse_education_segment(f"bachelor of science {bachelor_match.group(1)}", 'Bachelor of Science')
            if edu_entry:
                education.append(edu_entry)
        
        # Intermediate (12th)
        intermediate_match = re.search(r'intermediate(?:\s+that is)?\s+12th standard(.+?)(?:my secondary|secondary school|10th standard)', edu_text, re.IGNORECASE | re.DOTALL)
        if intermediate_match:
            edu_entry = self._parse_education_segment(f"intermediate 12th standard {intermediate_match.group(1)}", '12th Standard (Intermediate)')
            if edu_entry:
                education.append(edu_entry)
        
        # Secondary (10th)
        secondary_match = re.search(r'(?:my )?secondary school(?:\s+that is)?\s+10th standard(.+?)(?:thank you|$)', edu_text, re.IGNORECASE | re.DOTALL)
        if secondary_match:
            edu_entry = self._parse_education_segment(f"secondary school 10th standard {secondary_match.group(1)}", '10th Standard')
            if edu_entry:
                education.append(edu_entry)
        
        return education
    
    def _parse_education_segment(self, segment: str, qualification: str) -> Optional[Dict[str, Any]]:
        """Parse a single education segment"""
        edu = {
            'qualification': qualification,
            'specialization': '',
            'college': '',
            'university': '',
            'year_of_passing': '',
            'percentage': ''
        }
        
        # Extract specialization/branch
        spec_patterns = [
            r'(?:the )?branch (?:is )?([^,\.]+?)(?:\.|,|my college|college name)',
            r'(?:specialization|stream) (?:is )?([^,\.]+?)(?:\.|,|college)'
        ]
        for pattern in spec_patterns:
            spec_match = re.search(pattern, segment, re.IGNORECASE)
            if spec_match:
                edu['specialization'] = spec_match.group(1).strip().upper()
                break
        
        # Extract college/school
        college_patterns = [
            r'(?:my )?college (?:name )?(?:is )?([^,\.]+?)(?:\.|,|at |university)',
            r'(?:my )?school (?:name )?(?:is )?([^,\.]+?)(?:\.|,|board|university)',
            r'(?:in|from) ([^,\.]+?(?:college|school)[^,\.]*?)(?:\.|,|at |university|board)'
        ]
        for pattern in college_patterns:
            college_match = re.search(pattern, segment, re.IGNORECASE)
            if college_match:
                edu['college'] = college_match.group(1).strip().title()
                break
        
        # Extract university/board
        uni_patterns = [
            r'(?:university|board) (?:name )?(?:is )?([^,\.]+?)(?:\.|,|the year|year of|my percentage|\d)',
            r'(?:at |from )([^,\.]+?(?:university|board)[^,\.]*?)(?:\.|,|the year|year of|\d)',
            r'(?:university|board)[,\s]+([^,\.]+?)(?:\.|,|year|\d)'
        ]
        for pattern in uni_patterns:
            uni_match = re.search(pattern, segment, re.IGNORECASE)
            if uni_match:
                edu['university'] = uni_match.group(1).strip().title()
                break
        
        # Extract year of passing
        year_patterns = [
            r'(?:the )?year (?:of passing )?(?:is )?(\d{4})',
            r'passing (?:year )?(?:is )?(\d{4})',
            r'(?:at |in )(\d{4})',
            r'(\d{4})[,\s]*(?:and|,|\.)?\s*(?:\d+\s*percentage|my percentage)'
        ]
        for pattern in year_patterns:
            year_match = re.search(pattern, segment)
            if year_match:
                edu['year_of_passing'] = year_match.group(1)
                break
        
        # Extract percentage
        perc_patterns = [
            r'(\d+)\s*(?:%|percentage)',
            r'(?:percentage is |got |scored )(\d+)',
            r'year of passing[^,\.]*?(\d+)\s*percentage'
        ]
        for pattern in perc_patterns:
            perc_match = re.search(pattern, segment, re.IGNORECASE)
            if perc_match:
                edu['percentage'] = f"{perc_match.group(1)}%"
                break
        
        return edu
    
    def _parse_skill_list(self, text: str) -> List[str]:
        """Parse a comma/and separated list of skills"""
        if not text:
            return []
        
        # Clean up text
        text = text.replace(' and ', ', ')
        text = text.replace('such as', '')
        text = text.replace('including', '')
        
        # Split by comma
        items = [item.strip() for item in text.split(',')]
        
        # Clean and title case
        cleaned = []
        for item in items:
            item = item.strip()
            if item and len(item) > 1:
                # Preserve certain capitalizations
                if item.lower() in ['aws', 'gcp', 'adf', 'adls', 'cicd', 'dto', 'db2', 'mysql']:
                    cleaned.append(item.upper())
                else:
                    cleaned.append(item.title())
        
        return cleaned


# Example usage and testing
if __name__ == '__main__':
    # Test with sample transcript
    sample_transcript = """
    My name is Sriram Janga. My portal ID is abc123. My current grade is 11. 
    I can reach it at 988-124-8765. My email address is sriram.janga@nttdata.com.
    Coming to my professional summary, I have over 16 years of experience...
    """
    
    extractor = VoiceTranscriptEnhancedExtractor()
    result = extractor.extract_comprehensive(sample_transcript)
    
    import json
    logger.info(json.dumps(result, indent=2))
