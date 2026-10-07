"""
LLM Client for Ollama integration
"""

import requests
from config import OLLAMA_BASE_URL


def generate(model: str, prompt: str, system: str = "", temperature: float = 0.3) -> str:
    """Generate text using Ollama API."""
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "system": system,
                "options": {"temperature": temperature},
                "stream": False
            },
            timeout=600,
        )
        resp.raise_for_status()
        return resp.json()["response"]
    except Exception as e:
        print(f"Error calling Ollama: {str(e)}")
        raise


def generate_json(model: str, prompt: str, system: str = "", temperature: float = 0.3) -> dict:
    """Generate JSON response using Ollama API."""
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt + "\n\nReturn ONLY valid JSON, no other text.",
                "system": system,
                "options": {"temperature": temperature},
                "stream": False
            },
            timeout=600,
        )
        resp.raise_for_status()
        response_text = resp.json()["response"]
        
        # Try to extract JSON from response
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            import json as json_module
            return json_module.loads(json_match.group())
        else:
            raise ValueError("No JSON found in response")
    except Exception as e:
        print(f"Error parsing JSON from Ollama: {str(e)}")
        raise
