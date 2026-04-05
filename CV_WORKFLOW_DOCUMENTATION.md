# CV Builder Automation - Complete Workflow Documentation

## Overview

This document describes the complete AI-based CV processing workflow implemented in the CV Builder Automation system.

## Architecture

The system implements a comprehensive pipeline:

```
Upload CV
   ↓
AI Extraction (structured data extraction from raw text)
   ↓
Schema Mapping (validate against canonical CV schema)
   ↓
RAG Enrichment (normalize skills, standardize roles, enrich context)
   ↓
Validation (gap detection, quality assessment)
   ↓
Preview (formatted display with suggestions)
   ↓
Edit Loop (user edits with re-validation)
```

## Components

### 1. CV Workflow Orchestrator (`src/ai/services/cv_workflow_orchestrator.py`)

**Purpose**: Main orchestrator that manages the complete CV processing pipeline.

**Key Features**:
- Coordinates all workflow steps
- Manages workflow options (enable/disable specific steps)
- Handles error recovery
- Tracks workflow progress
- Generates comprehensive results

**Main Method**: `process_cv(cv_text, workflow_options)`

**Workflow Steps**:
1. **AI-based extraction** - Extract structured CV data from raw text
2. **Section detection** - Identify present/missing CV sections
3. **Schema mapping** - Validate against canonical schema
4. **RAG normalization** - Improve skills and standardize roles
5. **Gap detection** - Identify missing required/recommended fields
6. **Auto-suggestions** - Generate suggestions for improvements
7. **Quality improvement** - Assess and improve content quality
8. **Final validation** - Verify readiness for preview

### 2. CV Extraction Service (`src/ai/services/cv_extraction_service.py`)

**Purpose**: AI-powered extraction of structured data from CV text.

**Key Features**:
- **Structured extraction**: Converts raw CV text into structured JSON
- **Section detection**: Identifies different CV sections (skills, experience, education, etc.)
- **Gap detection**: Identifies missing required and recommended fields
- **Field normalization**: Standardizes field names and formats

**Main Methods**:
- `extract_structured_cv_data(cv_text)` - Extract complete CV data
- `detect_gaps(cv_data)` - Identify missing fields
- `_extract_basic_cv_data(cv_text)` - Fallback extraction when AI unavailable

**Extracted Sections**:
- Personal details (name, email, phone, location)
- Professional summary
- Skills (technical, soft, domain, tools, languages)
- Work experience with responsibilities
- Project experience
- Education
- Certifications
- Publications
- Awards
- Languages

### 3. RAG Normalization Service (`src/ai/services/rag_normalization_service.py`)

**Purpose**: Use Retrieval-Augmented Generation to improve and normalize CV content.

**Key Features**:

#### Skills Normalization
- Standardizes skill names (e.g., "JS" → "JavaScript")
- Groups related skills
- Suggests additional relevant skills
- Considers role context for suggestions

#### Role Standardization
- Maps non-standard job titles to industry-standard titles
- Preserves original role in metadata
- Considers seniority levels
- Industry-specific standardization

#### Context Enrichment
- Identifies domain expertise from skills and experience
- Determines career level (entry, mid, senior, lead, executive)
- Recommends relevant certifications
- Generates career insights

### 4. Quality Improvement Service (`src/ai/services/rag_normalization_service.py`)

**Purpose**: Assess and improve CV content quality.

**Key Features**:

#### Quality Assessment
Scores CVs across multiple dimensions:
- **Overall score** (0-100)
- **Completeness score** - How many sections are present
- **Detail quality score** - Quality of content in each section
- **Professional presentation score** - Formatting and clarity

**Output includes**:
- Numeric scores
- Strengths list
- Weaknesses list
- Actionable recommendations

#### Description Improvement
- Enhances experience descriptions
- Improves responsibility statements
- Adds quantifiable achievements
- Maintains professional tone

### 5. Upload CV Command (`src/application/commands/upload_cv.py`)

**Purpose**: Entry point for CV processing with workflow integration.

**Key Features**:
- File upload and text extraction (PDF, DOC, DOCX)
- Workflow orchestration
- Edit loop support with version tracking
- Result formatting for API responses

**Main Methods**:
- `execute(file_path, workflow_options)` - Process CV through workflow
- `apply_user_edits(workflow_result, edits)` - Apply and re-validate edits

## Setup and Configuration

### Prerequisites

1. **Python 3.8+**
2. **Required packages** (from pyproject.toml):
   - openai
   - langchain
   - python-docx
   - pypdf2

3. **Environment Variables**:
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

### Installation

```bash
# Install dependencies
pip install -r requirements.txt
# or
poetry install

# Verify installation
python test_complete_workflow.py
```

## Usage

### Basic Usage

```python
from src.application.commands.upload_cv import UploadCVCommand

# Initialize with workflow enabled
uploader = UploadCVCommand(use_workflow=True)

# Process CV with all features enabled
result = uploader.execute("path/to/cv.pdf")

# Access extracted data
cv_data = result["cv_data"]
validation = result["validation"]
suggestions = result["suggestions"]
```

### Customizing Workflow Options

```python
# Configure which steps to enable
workflow_options = {
    "enable_extraction": True,           # AI extraction
    "enable_section_detection": True,    # Section detection
    "enable_rag_normalization": True,    # Skills/role normalization
    "enable_gap_detection": True,        # Missing fields detection
    "enable_quality_improvement": True,  # Quality assessment
    "enable_auto_suggestions": True      # Auto-suggestions
}

result = uploader.execute("cv.pdf", workflow_options)
```

### Applying User Edits

```python
# User makes edits to CV data
edits = {
    "personal_details": {
        "phone": "+1-234-567-8900",
        "linkedin": "https://linkedin.com/in/user"
    },
    "skills": {
        "technical_skills": ["Python", "JavaScript", "React", "AWS"]
    }
}

# Apply edits and re-validate
updated_result = uploader.apply_user_edits(result, edits)

# Check validation
if updated_result["validation"]["final_validation"]["ready_for_preview"]:
    print("CV is ready for preview!")
```

### Accessing Results

```python
# Workflow metadata
metadata = result["metadata"]
print(f"Steps completed: {metadata['total_steps']}")
print(f"Sections detected: {metadata['sections_detected']['present_sections']}")

# CV data
cv_data = result["cv_data"]
personal = cv_data["personal_details"]
skills = cv_data["skills"]
experience = cv_data["experience"]

# Validation results
validation = result["validation"]
gaps = validation["gaps"]
quality = validation["quality_assessment"]
final_check = validation["final_validation"]

# Suggestions
suggestions = result["suggestions"]
field_suggestions = suggestions["field_suggestions"]
priority_actions = suggestions["priority_actions"]

# Preview
preview = result["preview"]
formatted_cv = preview["formatted_cv"]
```

## Workflow Details

### Step 1: AI-based Extraction

Extracts structured data from raw CV text using OpenAI GPT models.

**Input**: Raw CV text (string)
**Output**: Structured JSON with all CV sections

**Fallback**: If AI is unavailable, uses rule-based extraction

### Step 2: Section Detection

Identifies which CV sections are present or missing.

**Output**:
```json
{
  "present_sections": ["personal_details", "skills", "experience"],
  "missing_sections": ["certifications", "publications"],
  "section_completeness": 70.0
}
```

### Step 3: Schema Mapping

Validates extracted data against canonical CV schema.

**Checks**:
- Required fields presence
- Data type validation
- Structure validation

**Output**:
```json
{
  "valid": true,
  "errors": [],
  "warnings": ["Missing recommended field: personal_details.phone"]
}
```

### Step 4: RAG Normalization

Improves and standardizes CV content using RAG.

**Actions**:
- Normalize skill names
- Suggest additional skills based on role
- Standardize job titles
- Enrich with industry context

**Output**: Enhanced CV data with:
- `normalized_skills`
- `suggested_technical_skills`
- `standardized_roles` (with original preserved)
- `enrichments` (career level, domain expertise, recommendations)

### Step 5: Gap Detection

Identifies missing or incomplete fields.

**Output**:
```json
{
  "missing_required_fields": ["personal_details.email"],
  "missing_recommended_fields": ["certifications", "summary.professional_summary"],
  "gaps_detected": 3
}
```

### Step 6: Auto-Suggestions

Generates actionable suggestions for improvement.

**Types of suggestions**:
- **Field suggestions**: Missing fields to add
- **Content suggestions**: Ways to improve existing content
- **Priority actions**: Most important actions to take

**Output**:
```json
{
  "field_suggestions": [
    {
      "field": "professional_summary",
      "type": "required",
      "suggestion": "Add a compelling professional summary",
      "priority": "high"
    }
  ],
  "content_suggestions": [
    {
      "section": "experience",
      "suggestion": "Add more detailed responsibilities"
    }
  ],
  "priority_actions": [
    "Add professional_summary",
    "Add certifications"
  ]
}
```

### Step 7: Quality Improvement

Assesses overall CV quality and suggests improvements.

**Quality Scores**:
- Overall (0-100)
- Completeness (0-100)
- Detail Quality (0-100)
- Professional Presentation (0-100)

**Output**:
```json
{
  "overall_score": 75,
  "completeness_score": 80,
  "detail_quality_score": 70,
  "professional_presentation_score": 75,
  "strengths": [
    "Comprehensive technical skills listed",
    "Clear education history"
  ],
  "weaknesses": [
    "Experience descriptions lack quantifiable achievements",
    "Missing professional summary"
  ],
  "recommendations": [
    "Add metrics to experience descriptions",
    "Include a professional summary"
  ]
}
```

### Step 8: Final Validation

Performs final checks before allowing preview.

**Output**:
```json
{
  "ready_for_preview": true,
  "blocking_issues": [],
  "warnings": ["CV quality score is below 50"],
  "completeness_percentage": 80.0
}
```

## API Integration

### REST API Endpoint Example

```python
from fastapi import APIRouter, UploadFile, File
from src.application.commands.upload_cv import UploadCVCommand

router = APIRouter()

@router.post("/api/cv/upload")
async def upload_cv(
    file: UploadFile = File(...),
    enable_rag: bool = True,
    enable_quality_check: bool = True
):
    # Save uploaded file
    file_path = f"data/storage/{file.filename}"
    
    # Process through workflow
    uploader = UploadCVCommand(use_workflow=True)
    workflow_options = {
        "enable_rag_normalization": enable_rag,
        "enable_quality_improvement": enable_quality_check
    }
    
    result = uploader.execute(file_path, workflow_options)
    
    return {
        "status": result["status"],
        "cv_data": result["cv_data"],
        "validation": result["validation"],
        "suggestions": result["suggestions"],
        "preview": result["preview"]
    }

@router.post("/api/cv/edit")
async def apply_edits(cv_id: str, edits: dict):
    # Load existing result
    # Apply edits
    uploader = UploadCVCommand(use_workflow=True)
    updated_result = uploader.apply_user_edits(existing_result, edits)
    
    return updated_result
```

## Testing

### Running Tests

```bash
# Run complete workflow test
python test_complete_workflow.py

# Results saved to: workflow_test_results.json
```

### Test Output

The test demonstrates:
1. CV file upload and text extraction
2. Complete workflow execution
3. Detailed results for each step
4. Edit loop functionality
5. Final validation status

### Example Test Results

```
======================================================================
  WORKFLOW RESULTS
======================================================================

Status: COMPLETED
Steps Completed: 8
Steps: ai_extraction, section_detection, schema_mapping, rag_normalization, gap_detection, auto_suggestions, quality_assessment, final_validation

======================================================================
  METADATA
======================================================================

Extraction Method: AI
Total Steps: 8

Sections Detected: 7
Present: personal_details, summary, skills, experience, education
Completeness: 70.0%

======================================================================
  CV DATA SUMMARY
======================================================================

Name: John Doe
Email: john.doe@example.com
Phone: +1-234-567-8900
Current Role: Senior Software Engineer
Career Level: Senior

Technical Skills: 15
  Python, JavaScript, React, Node.js, AWS, Docker, Kubernetes, PostgreSQL, MongoDB, Redis...

AI-Suggested Skills: 5
  TypeScript, GraphQL, Terraform, Jenkins, Elasticsearch...

Work Experience: 3 entries
  1. Senior Software Engineer (standardized from 'Sr. Dev') at Tech Corp
  2. Software Engineer at StartupCo
  3. Junior Developer at FirstJob Inc

Education: 2 entries
Certifications: 1 entries

======================================================================
  VALIDATION RESULTS
======================================================================

Schema Valid: True
Warnings: 2
  [!] Missing recommended field: certifications
  [!] Missing recommended field: publications

Missing Required Fields: 0
Missing Recommended Fields: 2
  [!] certifications
  [!] publications

Quality Scores:
  Overall: 78/100
  Completeness: 80/100
  Detail Quality: 75/100
  Professional Presentation: 80/100

Strengths:
  [+] Comprehensive technical skills listed
  [+] Clear work history with multiple roles
  [+] Educational qualifications well documented

Areas to Improve:
  [-] Add more quantifiable achievements
  [-] Include certifications if available
  [-] Consider adding projects section

Ready for Preview: True
Completeness: 70.0%

======================================================================
  AUTO-SUGGESTIONS
======================================================================

Field Suggestions: 3
  [HIGH] certifications: Consider adding relevant certifications to strengthen your CV
  [MEDIUM] publications: Consider adding publications to strengthen your CV
  [HIGH] professional_summary: Add a professional summary (2-3 sentences)

Content Suggestions: 2
  - Add more detailed responsibilities and achievements (aim for 4-6 bullet points)
  - You have only 15 technical skills listed. Consider adding more relevant skills

Priority Actions:
  [!] Add professional_summary
  [!] Add certifications
  [!] Improve experience descriptions
```

## Best Practices

### 1. Always Enable Full Workflow

For best results, enable all workflow steps:
```python
workflow_options = {
    "enable_extraction": True,
    "enable_section_detection": True,
    "enable_rag_normalization": True,
    "enable_gap_detection": True,
    "enable_quality_improvement": True,
    "enable_auto_suggestions": True
}
```

### 2. Handle Errors Gracefully

```python
result = uploader.execute(file_path)

if result["status"] == "error":
    print(f"Errors:
