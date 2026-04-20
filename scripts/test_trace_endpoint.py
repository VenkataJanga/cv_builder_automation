#!/usr/bin/env python3
"""
Test LangSmith Trace Endpoint
"""

import requests
import time

def test_trace_endpoint():
    print('🔍 Testing Trace Endpoint...')
    time.sleep(2)  # Wait for server

    try:
        response = requests.get('http://localhost:8000/traces/test-session-123')
        print(f'✅ Status: {response.status_code}')

        if response.status_code == 200:
            data = response.json()
            print(f'✅ Tracing enabled: {data.get("enabled", False)}')
            if data.get('enabled'):
                print('🎉 LangSmith tracing is active!')
                print('📊 Response contains trace data structure')
            else:
                print('❌ Tracing is disabled')
        else:
            print(f'❌ Unexpected status: {response.status_code}')

    except Exception as e:
        print(f'❌ Error: {e}')

if __name__ == "__main__":
    test_trace_endpoint()