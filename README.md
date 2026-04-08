# Conversational CV Builder Platform

An intelligent, conversational platform for building and exporting professional CVs using FastAPI, OpenAI, and modern web technologies. This platform enables users to create, edit, and export CVs through an intuitive chat interface and web UI.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [API Endpoints](#api-endpoints)
- [Project Structure](#project-structure)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [Contact](#contact)

## Features

✅ **Conversational CV Building** - Build CVs through an interactive chat interface
✅ **AI-Powered Content** - OpenAI integration for intelligent content suggestions
✅ **Multi-Format Export** - Export CVs as DOCX, PDF, and other formats
✅ **Voice Input Support** - Convert voice transcripts to CV content
✅ **CV Preview** - Real-time preview of CV layouts
✅ **Session Management** - Track and manage multiple CV sessions
✅ **Content Validation** - Validate CV content quality and completeness
✅ **Web UI** - Modern, user-friendly demo interface
✅ **RESTful API** - Comprehensive REST API for integration
✅ **Template System** - Multiple CV template options (Modern, Hybrid, Standard)

## Prerequisites

- **Python 3.10+** - Required runtime
- **pip or Poetry** - Package manager
- **OpenAI API Key** - For AI features
- **Optional**: Azure OpenAI credentials for Azure deployment

## Installation

### Step 1: Clone or Download the Project

```bash
# Navigate to the project directory
cd cv_builder_automation
```

### Step 2: Create a Virtual Environment

```bash
# Using Python venv
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

### Step 3: Install Dependencies

Using pip:
```bash
pip install -e .
```

Or using Poetry:
```bash
poetry install
```

### Step 4: Configure Environment Variables

1. Create or update the `.env` file in the project root with the following variables:

```env
# Environment
ENV=local
DEBUG=true

# Application Settings
APP_NAME=Conversational CV Builder
API_PREFIX=/api/v1

# OpenAI Configuration (Required)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_TEMPERATURE=0.1
OPENAI_MAX_TOKENS=4000
OPENAI_VERIFY_SSL=false

# LLM Enhancement Settings (for voice transcript enhancement)
LLM_ENHANCEMENT_MODEL=gpt-4o-mini
LLM_ENHANCEMENT_TEMPERATURE=0.3
LLM_ENHANCEMENT_MAX_TOKENS=2000
LLM_SUMMARY_MAX_TOKENS=500
LLM_ACHIEVEMENT_MAX_TOKENS=500

# Optional: Azure OpenAI Configuration
# AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
# AZURE_OPENAI_API_KEY=your_azure_openai_key
# AZURE_OPENAI_DEPLOYMENT=your_deployment_name
# AZURE_OPENAI_EMBEDDING_DEPLOYMENT=your_embedding_deployment
```

2. **Important**: Set your OpenAI API Key
   - Get your API key from [OpenAI Platform](https://platform.openai.com/api-keys)
   - Replace `your_openai_api_key_here` with your actual key

## Running the Application

### Option 1: Run with Python (Development)

```bash
# Make sure your virtual environment is activated
python run.py
```

The application will start on `http://localhost:8000` with hot reload enabled.

### Option 2: Run with Uvicorn (Production)

```bash
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Option 3: Run with Docker (Optional)

```bash
# Build the Docker image
docker build -t cv-builder .

# Run the container
docker run -p 8000:8000 --env-file .env cv-builder
```

### Access the Application

- **Web UI**: Navigate to `http://localhost:8000` in your browser
- **API Docs**: `http://localhost:8000/docs` (Swagger UI)
- **Alternative API Docs**: `http://localhost:8000/redoc` (ReDoc)
- **Health Check**: `http://localhost:8000/health`

## Configuration

### Environment Files

The application uses environment-based configuration with YAML templates:

- `config/environments/base.yaml` - Base configuration template
- `config/environments/dev.yaml` - Development-specific settings
- Create additional environment files as needed (e.g., `prod.yaml`, `staging.yaml`)

### Template Configuration

CV templates are configured in `config/templates/`. The system supports:
- **Modern** - Contemporary, minimalist design
- **Hybrid** - Mixed traditional and modern elements
- **Standard** - Classic professional format

### Prompt Configuration

AI prompt templates are stored in `config/prompts/` for customizing AI responses.

## API Endpoints

The API provides the following main endpoint categories:

### Health Check
- `GET /health` - Application health status

### Chat
- `POST /api/v1/chat/message` - Send chat messages
- `POST /api/v1/chat/history` - Get conversation history

### Session Management
- `POST /api/v1/sessions` - Create new CV session
- `GET /api/v1/sessions/{session_id}` - Get session details
- `PUT /api/v1/sessions/{session_id}` - Update session
- `DELETE /api/v1/sessions/{session_id}` - Delete session

### CV Management
- `POST /api/v1/cv/create` - Create new CV
- `GET /api/v1/cv/{cv_id}` - Get CV details
- `PUT /api/v1/cv/{cv_id}` - Update CV
- `DELETE /api/v1/cv/{cv_id}` - Delete CV

### Preview
- `POST /api/v1/preview` - Generate CV preview
- `GET /api/v1/preview/{preview_id}` - Get preview status

### Export
- `POST /api/v1/export` - Export CV (DOCX, PDF)
- `GET /api/v1/export/{export_id}` - Download exported file
- `GET /api/v1/export/{export_id}/status` - Check export status

### Speech-to-Text
- `POST /api/v1/speech/transcribe` - Transcribe audio to text
- `POST /api/v1/speech/enhance` - Enhance transcribed content

### Validation
- `POST /api/v1/validation/validate` - Validate CV content
- `POST /api/v1/validation/suggestions` - Get improvement suggestions

### Retrieval
- `POST /api/v1/retrieval/search` - Search CV content
- `POST /api/v1/retrieval/embed` - Generate content embeddings

For detailed API documentation, visit `http://localhost:8000/docs` when the application is running.

## Project Structure

```
cv_builder_automation/
├── apps/
│   ├── api/                    # FastAPI application
│   │   ├── main.py            # Main FastAPI app setup
│   │   ├── dependencies.py     # Dependency injection
│   │   ├── bootstrap/          # Application initialization
│   │   └── middleware/         # Custom middleware
│   └── worker/                 # Background job processing
│
├── src/                        # Core application code
│   ├── ai/                     # AI/ML integration (OpenAI, embeddings)
│   ├── application/            # Business logic & use cases
│   ├── core/                   # Core utilities (env loader, config)
│   ├── domain/                 # Domain models & entities
│   ├── infrastructure/         # External integrations
│   ├── interfaces/             # REST API routers
│   │   └── rest/
│   │       └── routers/        # Endpoint definitions
│   ├── observability/          # Logging & monitoring
│   ├── orchestration/          # Workflow coordination
│   ├── questionnaire/          # Form & questionnaire logic
│   ├── retrieval/              # Information retrieval (RAG)
│   ├── templates/              # CV template engines
│   └── web/                    # Web UI utilities
│
├── config/                     # Configuration files
│   ├── environments/           # Environment-specific config
│   ├── prompts/               # AI prompt templates
│   ├── questionnaire/         # Questionnaire definitions
│   ├── security/              # Security settings
│   └── templates/             # CV templates
│
├── data/                       # Data storage
│   └── storage/               # Local file storage
│
├── demo-ui/                    # Frontend web application
│   ├── index.html
│   ├── app.js
│   └── styles.css
│
├── deployments/                # Deployment configurations
│   ├── aca/                    # Azure Container Apps
│   ├── aks/                    # Azure Kubernetes Service
│   ├── local/                  # Local deployment
│   └── scripts/                # Deployment scripts
│
├── docs/                       # Documentation
├── .env                        # Environment variables
├── .gitignore                  # Git ignore rules
├── pyproject.toml              # Project metadata & dependencies
├── poetry.lock                 # Locked dependency versions
└── README.md                   # This file
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run tests with verbose output
pytest -v

# Run specific test file
pytest tests/test_chat.py

# Run with coverage report
pytest --cov=src
```

### Browser Preview Renderer Test

A lightweight browser-based test harness is available for validating the client preview renderer:

1. Open `demo-ui/preview-renderer-test.html` in your browser.
2. The page will instantiate `demo-ui/app.js` in test mode and verify that preview HTML renders:
   - full name
   - current title
   - professional summary
   - education entries
3. The page displays pass/fail status and renders the generated preview output.

### Code Structure

- **Domain Layer** (`src/domain/`) - Business entities and interfaces
- **Application Layer** (`src/application/`) - Use cases and business logic
- **Infrastructure Layer** (`src/infrastructure/`) - External service integrations
- **Interface Layer** (`src/interfaces/`) - HTTP API endpoints
- **Core Layer** (`src/core/`) - Shared utilities and configuration

### Adding New Features

1. Define domain models in `src/domain/`
2. Implement use cases in `src/application/`
3. Add API endpoints in `src/interfaces/rest/routers/`
4. Create integration tests in `tests/`
5. Update API documentation

### Code Style

The project follows PEP 8 guidelines. Format code using:

```bash
# Using black (install: pip install black)
black .

# Check code quality
pylint src/
```

## Troubleshooting

### Issue: "OpenAI API Key not found"
**Solution**: Ensure `OPENAI_API_KEY` is set correctly in your `.env` file. Restart the application after updating.

### Issue: ImportError on startup
**Solution**: Make sure all dependencies are installed:
```bash
pip install -e .
# or
poetry install
```

### Issue: Port 8000 already in use
**Solution**: Use a different port:
```bash
python run.py  # Check run.py for port configuration
# or manually specify
uvicorn apps.api.main:app --port 8001
```

### Issue: CORS errors when accessing from frontend
**Solution**: The CORS middleware is already configured to allow all origins in development. For production, update `apps/api/main.py`:
```python
CORSMiddleware(
    allow_origins=["https://yourdomain.com"],  # Specify your domain
    ...
)
```

### Issue: Speech-to-Text or Audio features not working
**Solution**: Verify your OpenAI API key supports audio APIs (Whisper). Check API limits and quotas.

### Debug Mode

Enable detailed logging:
```bash
# Set in .env
DEBUG=true
ENV=local
```

Check logs in the console for detailed error information.

## Contact & Support

- **Author**: NTT DATA
- **Email**: venkatakirankumar.janga@nttdata.com
- **Project**: Conversational CV Builder Platform v0.1.0

For issues, questions, or contributions, please contact the project maintainer.

---

**Last Updated**: April 2026
**Version**: 0.1.0
