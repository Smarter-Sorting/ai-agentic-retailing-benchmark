"""LLM client abstraction for Anthropic Claude and Google Gemini APIs."""

import json
import logging
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)


def evaluate_with_anthropic(prompt, api_key, model=None):
    """Send evaluation prompt to Anthropic Claude API.

    Args:
        prompt: The complete evaluation prompt.
        api_key: Anthropic API key.
        model: Model ID (defaults to claude-sonnet-4-20250514).

    Returns:
        dict with response text or error.
    """
    model = model or "claude-sonnet-4-20250514"
    url = "https://api.anthropic.com/v1/messages"

    payload = {
        "model": model,
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}],
    }

    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }

    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
            # Extract text from Claude response
            text = ""
            for block in data.get("content", []):
                if block.get("type") == "text":
                    text += block.get("text", "")
            return {"success": True, "text": text, "raw": data}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
        logger.error("Anthropic API error %s: %s", exc.code, detail)
        return {"success": False, "error": f"Anthropic HTTP {exc.code}: {detail}"}
    except Exception as exc:
        logger.error("Anthropic API unexpected error: %s", exc)
        return {"success": False, "error": str(exc)}


def evaluate_with_gemini(prompt, api_key, model=None):
    """Send evaluation prompt to Google Gemini API.

    Args:
        prompt: The complete evaluation prompt.
        api_key: Google AI API key.
        model: Model ID (defaults to gemini-2.0-flash).

    Returns:
        dict with response text or error.
    """
    model = model or "gemini-2.0-flash"
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
        f":generateContent?key={api_key}"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 4096,
        },
    }

    headers = {"Content-Type": "application/json"}
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
            # Extract text from Gemini response
            text = ""
            for candidate in data.get("candidates", []):
                content = candidate.get("content", {})
                for part in content.get("parts", []):
                    text += part.get("text", "")
            return {"success": True, "text": text, "raw": data}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
        logger.error("Gemini API error %s: %s", exc.code, detail)
        return {"success": False, "error": f"Gemini HTTP {exc.code}: {detail}"}
    except Exception as exc:
        logger.error("Gemini API unexpected error: %s", exc)
        return {"success": False, "error": str(exc)}


def parse_llm_response(response_text):
    """Parse the LLM response text into structured JSON.

    Handles cases where the LLM wraps JSON in markdown code blocks.

    Args:
        response_text: Raw text from LLM.

    Returns:
        Parsed dict or None if parsing fails.
    """
    if not response_text:
        return None

    text = response_text.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```)
        lines = lines[1:]
        # Remove last line (```)
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
        logger.warning("Failed to parse LLM response as JSON")
        return None
