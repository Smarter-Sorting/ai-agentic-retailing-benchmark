def load_env_file(path):
    # Read KEY=VALUE lines from an env file into a dict.
    env = {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip()
    except FileNotFoundError:
        pass
    return env


def load_platform_config(platform_id, env):
    # Build a config dict for a platform from env values.
    key_prefix = platform_id.upper()
    base_url = _clean_env_value(env.get(f"{key_prefix}_BASE_URL"))
    api_key = _clean_env_value(env.get(f"{key_prefix}_API_KEY"))
    model = _clean_env_value(env.get(f"{key_prefix}_MODEL"))
    if not api_key:
        return None
    if _requires_base_url(platform_id) and not base_url:
        return None
    if api_key.startswith("Bearer "):
        api_key = api_key[len("Bearer ") :]
    return {"base_url": base_url, "api_key": api_key, "model": model}


def _clean_env_value(value):
    # Strip quotes and whitespace from env values.
    if value is None:
        return ""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1].strip()
    return value


def _requires_base_url(platform_id):
    # Gemini uses the genai SDK, others require HTTP base URL.
    return platform_id.upper() != "GEMINI"
