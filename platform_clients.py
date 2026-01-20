import json
import os
import urllib.request


def execute_prompt(platform_id, prompt, config):
    # Send a prompt to a REST-backed platform and return raw response text.
    if not config:
        raise ValueError(f"Missing config for platform_id={platform_id}")
    platform_id = platform_id.upper()

    if platform_id == "CHATGPT":
        payload = _build_chatgpt_payload(prompt, config.get("model"))
        return _post_json(config["base_url"], config["api_key"], payload)

    if platform_id == "PERPLEX":
        payload = _build_messages_payload(prompt, config.get("model"))
        return _post_json(config["base_url"], config["api_key"], payload)

    if platform_id == "CLAUDE":
        payload = _build_claude_payload(prompt, config.get("model"))
        return _post_json(
            config["base_url"],
            config["api_key"],
            payload,
            extra_headers={"anthropic-version": "2023-06-01"},
            auth_header="x-api-key",
        )

    if platform_id == "GEMINI":
        raise ValueError("GEMINI requests use google-genai; call execute_gemini_prompt.")

    if platform_id == "COPILOT":
        payload = _build_messages_payload(prompt, config.get("model"))
        return _post_json(config["base_url"], config["api_key"], payload)

    raise ValueError(f"Unknown platform_id={platform_id}")


def execute_gemini_prompt(prompt, config):
    # Send a prompt through google-genai and return raw + text responses.
    try:
        from google import genai
    except ImportError as exc:
        raise ValueError(
            "Missing google-genai. Install with: pip install -q -U google-genai"
        ) from exc

    model = (config.get("model") or "").strip()
    if not model:
        raise ValueError("Missing GEMINI_MODEL")

    # Force API-key mode for AI Studio keys (avoid Vertex-only auth).
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "0")
    client = _create_genai_client(genai, config["api_key"])
    try:
        response = client.models.generate_content(model=model, contents=prompt)
    except Exception as exc:
        message = str(exc)
        if "API keys are not supported by this API" in message:
            raise ValueError(
                "Gemini API key rejected. Ensure you're using an AI Studio key "
                "and no Vertex-only settings (e.g. GOOGLE_GENAI_USE_VERTEXAI)."
            ) from exc
        raise
    full_response = _serialize_genai_response(response)
    text_response = _extract_genai_text(response)
    return full_response, text_response


def _build_chatgpt_payload(prompt, model):
    # Build ChatGPT-specific request payload.
    return {"model": model, "input": prompt}


def _build_messages_payload(prompt, model):
    # Build generic chat messages payload.
    return {"model": model, "messages": [{"role": "user", "content": prompt}]}


def _build_claude_payload(prompt, model, max_tokens=1024):
    # Build Claude-specific request payload.
    return {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }


def _extract_genai_text(response):
    # Pull best-effort text from genai responses.
    text = getattr(response, "text", None)
    if text:
        return text
    candidates = getattr(response, "candidates", None) or []
    parts = []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        if not content:
            continue
        for part in getattr(content, "parts", None) or []:
            value = getattr(part, "text", None)
            if value:
                parts.append(value)
    return "".join(parts)


def _serialize_genai_response(response):
    # Serialize genai response objects to JSON.
    for attr in ("model_dump_json", "to_json", "json"):
        method = getattr(response, attr, None)
        if callable(method):
            try:
                value = method()
            except TypeError:
                continue
            if isinstance(value, str):
                return value
            return json.dumps(value, ensure_ascii=True, default=str)
    try:
        return json.dumps(response, ensure_ascii=True, default=str)
    except TypeError:
        return str(response)


def _create_genai_client(genai_module, api_key):
    # Try API-key auth options for genai client init.
    for kwargs in ({"api_key": api_key, "vertexai": False}, {"api_key": api_key}):
        try:
            return genai_module.Client(**kwargs)
        except TypeError:
            continue
    return genai_module.Client(api_key=api_key)


def _post_json(url, api_key, payload, extra_headers=None, auth_header="Authorization"):
    # POST JSON payload and return the response text.
    body = json.dumps(payload).encode("utf-8")
    auth_value = f"Bearer {api_key}" if auth_header.lower() == "authorization" else api_key
    headers = {
        "Content-Type": "application/json",
        auth_header: auth_value,
    }
    if extra_headers:
        headers.update(extra_headers)
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        # Bubble up API error bodies for easier debugging.
        detail = exc.read().decode("utf-8", errors="replace")
        raise urllib.error.HTTPError(
            exc.url, exc.code, f"{exc.msg}: {detail}", exc.hdrs, exc.fp
        ) from exc
