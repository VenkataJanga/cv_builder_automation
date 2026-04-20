@echo off
REM LangSmith Environment Setup Batch File
REM Run this to set up LangSmith tracing for the current session

echo Setting up LangSmith environment variables...

set LANGSMITH_ENABLED=true
set LANGSMITH_API_KEY=<YOUR_LANGSMITH_API_KEY>
set LANGCHAIN_PROJECT=cv-builder
set LANGSMITH_ENDPOINT=https://api.smith.langchain.com

echo ✅ LangSmith environment variables set!
echo LANGSMITH_ENABLED: %LANGSMITH_ENABLED%
echo LANGCHAIN_PROJECT: %LANGCHAIN_PROJECT%
echo LANGSMITH_ENDPOINT: %LANGSMITH_ENDPOINT%
echo LANGSMITH_API_KEY: configured
echo.
echo 🔍 Testing LangSmith connection...

python -c "import sys, os; sys.path.insert(0, os.getcwd()); from src.observability.langsmith_tracer import get_langsmith_tracer; tracer = get_langsmith_tracer(); print(f'✅ Tracer enabled: {tracer.enabled}'); print(f'✅ LangSmith client available: {tracer.langsmith_client is not None}'); print('🎉 LangSmith integration ready!' if tracer.langsmith_client else '❌ LangSmith client not initialized')"

echo.
echo 📋 Next steps:
echo 1. Run your CV Builder application in this command window
echo 2. Check traces at: GET /traces/{session_id}
echo 3. View traces in LangSmith dashboard: https://smith.langchain.com/
echo.
echo 💡 These variables are only active in this command session
echo 💡 For permanent setup, add them to your system environment variables

pause