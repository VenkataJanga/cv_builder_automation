#!/usr/bin/env python3
"""
Simple API key validation script - run directly to check if API key works.
Usage: python scripts/test_api_key.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def test_api_key_validation():
    """Validate API key configuration and connectivity."""
    
    print_section("API Key Validation Test")
    
    # Load environment variables
    print("\n[1] Loading environment variables...")
    try:
        from src.core.env_loader import load_environment_variables
        load_environment_variables()
        print("✓ Environment variables loaded successfully")
    except Exception as e:
        print(f"✗ Failed to load environment variables: {e}")
        return False

    # Check API key existence
    print("\n[2] Checking OPENAI_API_KEY configuration...")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("✗ OPENAI_API_KEY not found in environment")
        return False
    
    if not api_key.strip():
        print("✗ OPENAI_API_KEY is empty")
        return False
    
    print(f"✓ API Key found: {api_key[:15]}...{api_key[-10:]}")
    
    # Validate API key format
    print("\n[3] Validating API key format...")
    if api_key.startswith("sk-"):
        print("✓ API key format is valid (starts with 'sk-')")
    else:
        print(f"✗ Invalid API key format: {api_key[:20]}...")
        return False

    # Check model configuration
    print("\n[4] Checking model configuration...")
    model = os.getenv("OPENAI_MODEL")
    embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL")
    print(f"  - Chat Model: {model}")
    print(f"  - Embedding Model: {embedding_model}")
    if model and embedding_model:
        print("✓ Model configuration complete")
    else:
        print("✗ Model configuration missing")
        return False

    # Test OpenAI client initialization
    print("\n[5] Initializing OpenAI client...")
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        print("✓ OpenAI client initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize OpenAI client: {e}")
        return False

    # Test Chat API connectivity
    print("\n[6] Testing OpenAI Chat API...")
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Reply with: API key is valid"}
            ],
            temperature=0.1,
            max_tokens=50
        )
        
        if response and response.choices and response.choices[0].message.content:
            print(f"✓ Chat API working - Response: {response.choices[0].message.content}")
        else:
            print("✗ Chat API returned empty response")
            return False
            
    except Exception as e:
        print(f"✗ Chat API failed: {e}")
        return False

    # Test Embedding API connectivity
    print("\n[7] Testing OpenAI Embedding API...")
    try:
        response = client.embeddings.create(
            model=embedding_model,
            input="API key validation test"
        )
        
        if response and response.data and response.data[0].embedding:
            embedding_size = len(response.data[0].embedding)
            print(f"✓ Embedding API working - Vector size: {embedding_size}")
        else:
            print("✗ Embedding API returned empty response")
            return False
            
    except Exception as e:
        print(f"✗ Embedding API failed: {e}")
        return False

    return True


def main():
    """Main entry point."""
    try:
        success = test_api_key_validation()
        
        print_section("Test Summary")
        if success:
            print("\n✓✓✓ All tests passed! API key is working correctly. ✓✓✓\n")
            return 0
        else:
            print("\n✗✗✗ Some tests failed. Please check your configuration. ✗✗✗\n")
            return 1
            
    except Exception as e:
        print_section("Error")
        print(f"\n✗ Unexpected error: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
