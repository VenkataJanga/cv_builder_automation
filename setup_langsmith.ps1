# LangSmith Environment Setup Script
# Run this script to set up LangSmith tracing environment variables

# Set LangSmith configuration
$env:LANGSMITH_ENABLED = "true"
$env:LANGSMITH_API_KEY = "<YOUR_LANGSMITH_API_KEY>"
$env:LANGCHAIN_PROJECT = "cv-builder"
$env:LANGSMITH_ENDPOINT = "https://api.smith.langchain.com"

Write-Host "✅ LangSmith environment variables set!"
Write-Host "LANGSMITH_ENABLED: $env:LANGSMITH_ENABLED"
Write-Host "LANGCHAIN_PROJECT: $env:LANGCHAIN_PROJECT"
Write-Host "LANGSMITH_ENDPOINT: $env:LANGSMITH_ENDPOINT"
Write-Host "LANGSMITH_API_KEY: configured"
Write-Host ""
Write-Host "🔍 Testing LangSmith connection..."

# Test the setup
python -c "
import sys
sys.path.insert(0, r'$(Get-Location)')
from src.observability.langsmith_tracer import get_langsmith_tracer
tracer = get_langsmith_tracer()
print(f'✅ Tracer enabled: {tracer.enabled}')
print(f'✅ LangSmith client available: {tracer.langsmith_client is not None}')
if tracer.langsmith_client:
    print('🎉 LangSmith integration ready!')
else:
    print('❌ LangSmith client not initialized')
"

Write-Host ""
Write-Host "📋 Next steps:"
Write-Host "1. Run your CV Builder application with these environment variables"
Write-Host "2. Check traces at: GET /traces/{session_id}"
Write-Host "3. View traces in LangSmith dashboard: https://smith.langchain.com/"
Write-Host ""
Write-Host "💡 To make these permanent, add them to your PowerShell profile or system environment variables"