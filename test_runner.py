import json
import os
import re
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import load_env_file, load_platform_config
from platform_clients import execute_prompt, execute_gemini_prompt
from reporting import (
    build_report_path,
    extract_fieldnames,
    format_scenario,
    result_key,
    write_report,
)
from product_ground_truth_loader import load_product_ground_truth
from test_loader import load_tests_xlsx


CLAUDE_DELAY_SECONDS = 10
STEP_RETRY_COUNT = 2
STEP_RETRY_BACKOFF_SECONDS = 5
SCORING_FIELDS = [
    "identity_accuracy_score",
    "attribute_completeness_score",
    "attribute_correctness_score",
    "regulatory_correctness_score",
    "transactional_reliability_score",
    "step_outcome",
    "failure_modes",
    "instant_checkout_feasibility_score",
    "checkout_failure_modes",
    "efficiency_score",
    "query_to_product_match_score",
    "agent_failure_modes",
    "comments",
]


def _run_platform_sequence(
    platform_id,
    scenario_steps,
    env,
    scoring_platform_id,
    scoring_config,
    scoring_prompt_template,
    ground_truth_by_sku,
    results,
    filtered_rows,
    report_path,
    report_lock,
):
    config = load_platform_config(platform_id, env)
    for scenario_id, steps in scenario_steps:
        _log(
            f"Running scenario_id={scenario_id} platform_id={platform_id} steps={len(steps)}"
        )
        history = []
        for step in steps:
            step_scenario_id, step_platform_id = _resolve_step_identity(
                scenario_id, platform_id, step
            )
            prompt = step.get("user_prompt", "")
            full_prompt = _build_conversation_prompt(history, prompt)
            _log(
                "Executing step "
                f"scenario_id={step_scenario_id} platform_id={step_platform_id} "
                f"step_id={step.get('step_id', '')} step_index={step.get('step_index', '')}"
            )
            comments = ""
            scoring_values = {}
            scoring_error = ""
            try:
                response, text_response = _execute_step_with_retries(
                    step_platform_id,
                    full_prompt,
                    config,
                    step_scenario_id,
                    step,
                )
                _maybe_throttle(step_platform_id)
                scoring_values, scoring_error = _score_step(
                    scoring_platform_id,
                    scoring_config,
                    scoring_prompt_template,
                    ground_truth_by_sku,
                    step,
                    text_response,
                )
                comments = scoring_values.pop("comments", "")
            except Exception as exc:
                response = ""
                text_response = ""
                comments = f"Unexpected error: {type(exc).__name__}: {exc}"
                _log(
                    "Unexpected error while executing step "
                    f"scenario_id={step_scenario_id} platform_id={step_platform_id} "
                    f"step_id={step.get('step_id', '')} step_index={step.get('step_index', '')}: "
                    f"{type(exc).__name__}: {exc}"
                )
            if scoring_error:
                comments = _join_comment(comments, scoring_error)
            result = {
                "scenario_id": step_scenario_id,
                "platform_id": step_platform_id,
                "step_id": step.get("step_id", ""),
                "step_index": step.get("step_index", ""),
                "user_prompt": prompt,
                "model_response": text_response,
                "full_model_response": response,
                "text_model_response": text_response,
                "comments": comments,
                "run_id": step.get("run_id", ""),
                "step_type": step.get("step_type", ""),
                **scoring_values,
            }
            _append_conversation_turn(history, prompt, text_response)
            with report_lock:
                results.append(result)
                write_report(results, filtered_rows, report_path=report_path)
            _log(
                "Updated report after step "
                f"scenario_id={step_scenario_id} platform_id={step_platform_id} "
                f"step_id={step.get('step_id', '')} step_index={step.get('step_index', '')}"
            )


def run_tests(
    xlsx_path,
    env_path=".env",
    platform_id=None,
    scenario_start=None,
    scenario_end=None,
    ground_truth_path=None,
    scoring_prompt_path=None,
    scoring_platform_id=None,
    excluded_platforms=None,
):
    # Execute test steps and return a list of result dicts.
    if not xlsx_path:
        raise ValueError("xlsx_path is required.")
    _log(f"Loading test rows from {xlsx_path}")
    env = load_env_file(env_path)
    scoring_platform_id = scoring_platform_id or None
    scoring_config = None
    if scoring_platform_id:
        scoring_config = load_platform_config(scoring_platform_id, env)
        if not scoring_config:
            _log(
                f"Missing scoring config for platform_id={scoring_platform_id}; skipping scoring."
            )
            scoring_platform_id = None

    if scoring_prompt_path and os.path.exists(scoring_prompt_path):
        scoring_prompt_template = _load_scoring_prompt_template(scoring_prompt_path)
    else:
        scoring_prompt_template = ""
        scoring_platform_id = None
        _log("Scoring prompt missing; skipping scoring.")

    if ground_truth_path and os.path.exists(ground_truth_path):
        ground_truth_by_sku = load_product_ground_truth(ground_truth_path)
    else:
        ground_truth_by_sku = {}
        scoring_platform_id = None
        _log("Ground truth missing; skipping scoring.")
    rows = load_tests_xlsx(xlsx_path)
    excluded_platforms = {p.upper() for p in (excluded_platforms or set())}
    if platform_id:
        if isinstance(platform_id, (set, list, tuple)):
            platform_items = platform_id
        else:
            platform_items = [platform_id]
        normalized = {item.strip().upper() for item in platform_items if item}
        rows = [
            row for row in rows if row.get("platform_id", "").upper() in normalized
        ]
        _log(f"Filtered rows to platform_id={sorted(normalized)}: {len(rows)} rows")
    if excluded_platforms:
        rows = [
            row
            for row in rows
            if row.get("platform_id", "").upper() not in excluded_platforms
        ]
        _log(
            "Filtered rows by excluded platforms "
            f"{sorted(excluded_platforms)}: {len(rows)} rows"
        )
    scenarios = _group_by_scenario(rows, scenario_start, scenario_end)
    filtered_rows = _flatten_scenarios(scenarios)
    _log(f"Loaded {len(filtered_rows)} rows across {len(scenarios)} scenarios")

    results = []
    report_lock = threading.Lock()
    report_path = build_report_path()
    write_report(results, filtered_rows, report_path=report_path)
    _log(f"Initialized report at {report_path}")
    platform_sequences = _build_platform_sequences(scenarios)
    max_workers = max(1, len(platform_sequences))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_platform = {}
        for platform_id, scenario_steps in platform_sequences.items():
            future = executor.submit(
                _run_platform_sequence,
                platform_id,
                scenario_steps,
                env,
                scoring_platform_id,
                scoring_config,
                scoring_prompt_template,
                ground_truth_by_sku,
                results,
                filtered_rows,
                report_path,
                report_lock,
            )
            future_to_platform[future] = platform_id
        for future in as_completed(future_to_platform):
            platform_id = future_to_platform[future]
            try:
                future.result()
            except Exception as exc:
                _log(
                    "Unexpected error while running platform "
                    f"platform_id={platform_id}: "
                    f"{type(exc).__name__}: {exc}"
                )
    _log(f"Wrote report for {len(results)} steps")
    return results


def _execute_step(platform_id, prompt, config):
    # Route step execution to the correct platform client.
    if not config:
        raise ValueError(f"Missing config for platform_id={platform_id}")
    platform_id = platform_id.upper()
    if platform_id == "GEMINI":
        return execute_gemini_prompt(prompt, config)
    response = execute_prompt(platform_id, prompt, config)
    text_response = _extract_text_response(platform_id, response)
    return response, text_response


def _execute_step_with_retries(platform_id, prompt, config, scenario_id, step):
    # Retry model calls a limited number of times before surfacing the error.
    last_exc = None
    total_attempts = STEP_RETRY_COUNT + 1
    for attempt in range(1, total_attempts + 1):
        try:
            return _execute_step(platform_id, prompt, config)
        except Exception as exc:
            last_exc = exc
            if attempt <= STEP_RETRY_COUNT:
                _log(
                    "Model call failed; retrying "
                    f"attempt={attempt}/{total_attempts} "
                    f"scenario_id={scenario_id} platform_id={platform_id} "
                    f"step_id={step.get('step_id', '')} step_index={step.get('step_index', '')}: "
                    f"{type(exc).__name__}: {exc}"
                )
                time.sleep(STEP_RETRY_BACKOFF_SECONDS * attempt)
                continue
            break
    raise last_exc


def _maybe_throttle(platform_id):
    # Apply per-platform rate limits.
    if platform_id.upper() == "CLAUDE":
        time.sleep(CLAUDE_DELAY_SECONDS)


def _score_step(
    scoring_platform_id,
    scoring_config,
    scoring_prompt_template,
    ground_truth_by_sku,
    step,
    model_response,
):
    # Score a step via the scoring platform and return normalized field values.
    if not scoring_platform_id or not scoring_config:
        return {}, ""
    if not scoring_prompt_template:
        return {field: "" for field in SCORING_FIELDS}, "Scoring prompt missing."
    if not model_response:
        return {field: "" for field in SCORING_FIELDS}, ""

    scoring_prompt = _build_scoring_prompt(
        scoring_prompt_template,
        step,
        model_response,
        ground_truth_by_sku,
    )
    try:
        scoring_raw = execute_prompt(scoring_platform_id, scoring_prompt, scoring_config)
        scoring_text = _extract_text_response(scoring_platform_id, scoring_raw)
        scores = _parse_scoring_response(scoring_text)
        normalized = {
            field: _normalize_scoring_value(scores.get(field, ""))
            for field in SCORING_FIELDS
        }
        return normalized, ""
    except Exception as exc:
        _log(
            "Unexpected error while scoring step "
            f"scenario_id={step.get('scenario_id', '')} platform_id={step.get('platform_id', '')} "
            f"step_id={step.get('step_id', '')} step_index={step.get('step_index', '')}: "
            f"{type(exc).__name__}: {exc}"
        )
        error = f"Scoring error: {type(exc).__name__}: {exc}"
        return {field: "" for field in SCORING_FIELDS}, error


def _join_comment(comment, extra):
    # Merge comment strings while preserving both when present.
    if not comment:
        return extra
    if not extra:
        return comment
    return f"{comment} | {extra}"


def _build_scoring_prompt(
    scoring_prompt_template,
    step,
    model_response,
    ground_truth_by_sku,
):
    # Fill the scoring prompt template with the current step + ground truth.
    sku_id = step.get("sku_id", "")
    ground_truth = ground_truth_by_sku.get(sku_id, "")
    return scoring_prompt_template.format(
        step_type=step.get("step_type", ""),
        user_prompt=step.get("user_prompt", ""),
        model_response=model_response,
        ground_truth=ground_truth,
    )


def _parse_scoring_response(scoring_text):
    # Parse JSON response, falling back to extracting the first JSON object.
    try:
        return json.loads(scoring_text)
    except (TypeError, ValueError):
        pass

    if not scoring_text:
        return {}

    start = scoring_text.find("{")
    end = scoring_text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    try:
        return json.loads(scoring_text[start : end + 1])
    except (TypeError, ValueError):
        return {}


def _log(message):
    print(message)


def _group_by_scenario(rows, scenario_start=None, scenario_end=None):
    # Group rows by scenario/platform and sort each group by step_index.
    scenarios = {}
    scenario_ids = sorted({row.get("scenario_id", "") for row in rows})
    scenario_ids = _filter_scenario_ids(scenario_ids, scenario_start, scenario_end)
    scenario_id_set = set(scenario_ids)
    for row in rows:
        scenario_id = row.get("scenario_id", "")
        if scenario_id not in scenario_id_set:
            continue
        platform_id = row.get("platform_id", "")
        scenarios.setdefault(scenario_id, {})
        scenarios[scenario_id].setdefault(platform_id, [])
        scenarios[scenario_id][platform_id].append(row)

    for platforms in scenarios.values():
        for platform_id, steps in platforms.items():
            platforms[platform_id] = sorted(
                steps, key=lambda r: _to_float(r.get("step_index", "0"))
            )
    return scenarios


def _filter_scenario_ids(scenario_ids, scenario_start, scenario_end):
    # Filter scenario ids to a start/end window (inclusive) when provided.
    if scenario_start is None and scenario_end is None:
        return scenario_ids
    start = scenario_start if scenario_start is not None else scenario_ids[0]
    end = scenario_end if scenario_end is not None else scenario_ids[-1]
    start_num = _parse_scenario_numeric(start)
    end_num = _parse_scenario_numeric(end)
    filtered = []
    for scenario_id in scenario_ids:
        scenario_num = _parse_scenario_numeric(scenario_id)
        if (start_num is not None or end_num is not None) and scenario_num is not None:
            if start_num is not None and scenario_num < start_num:
                continue
            if end_num is not None and scenario_num > end_num:
                continue
            filtered.append(scenario_id)
            continue
        if scenario_id < start or scenario_id > end:
            continue
        filtered.append(scenario_id)
    return filtered


def _parse_scenario_numeric(value):
    # Extract numeric suffix for IDs like Q001; return int or None.
    if value is None:
        return None
    text = str(value).strip()
    if text.isdigit():
        return int(text)
    match = re.match(r"^[A-Za-z]+([0-9]+)$", text)
    if not match:
        return None
    return int(match.group(1))


def _flatten_scenarios(scenarios):
    # Flatten grouped scenarios back into a list of rows.
    rows = []
    for scenario_id in sorted(scenarios.keys()):
        platforms = scenarios[scenario_id]
        for platform_id in sorted(platforms.keys()):
            rows.extend(platforms[platform_id])
    return rows


def _build_platform_sequences(scenarios):
    # Build ordered scenario lists per platform to avoid cross-platform blocking.
    platform_sequences = {}
    for scenario_id in sorted(scenarios.keys()):
        platforms = scenarios[scenario_id]
        for platform_id in sorted(platforms.keys()):
            platform_sequences.setdefault(platform_id, [])
            platform_sequences[platform_id].append((scenario_id, platforms[platform_id]))
    return platform_sequences


def _to_float(value):
    # Convert values to float for sorting, defaulting to 0.0.
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _extract_text_response(platform_id, response_text):
    # Extract plain text content from a response payload.
    platform_id = platform_id.upper()
    # Best-effort parsing of common response shapes.
    try:
        data = json.loads(response_text)
    except (TypeError, ValueError):
        return response_text or ""

    if platform_id == "CHATGPT":
        output_text = data.get("output_text")
        if output_text:
            return output_text
        output_items = data.get("output") or []
        texts = []
        for item in output_items:
            if item.get("type") != "message":
                continue
            for content in item.get("content") or []:
                text = content.get("text")
                if text:
                    texts.append(text)
        if texts:
            return "".join(texts)

    choices = data.get("choices")
    if choices:
        message = choices[0].get("message") if choices else None
        if message and message.get("content"):
            return message["content"]

    content = data.get("content")
    if isinstance(content, list):
        texts = [part.get("text", "") for part in content if isinstance(part, dict)]
        combined = "".join(texts)
        if combined:
            return combined

    return response_text or ""


def _build_conversation_prompt(history, user_prompt):
    # Build a plain-text conversation transcript for stateless APIs.
    parts = []
    for turn in history:
        role = turn.get("role")
        content = turn.get("content", "")
        if not content:
            continue
        label = "User" if role == "user" else "Assistant"
        parts.append(f"{label}: {content}")
    parts.append(f"User: {user_prompt}")
    return "\n".join(parts)


def _append_conversation_turn(history, user_prompt, assistant_response):
    # Append a user/assistant turn pair to conversation history.
    history.append({"role": "user", "content": user_prompt})
    history.append({"role": "assistant", "content": assistant_response})


def _normalize_scoring_value(value):
    # Normalize nulls to empty values for clean XLSX cells.
    if value is None:
        return ""
    return value


def _load_scoring_prompt_template(path):
    # Load the scoring prompt template from disk.
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except FileNotFoundError:
        return ""


def _resolve_step_identity(scenario_id, platform_id, step):
    # Prefer explicit step identifiers; warn if they disagree with grouping.
    step_scenario_id = step.get("scenario_id") or scenario_id
    step_platform_id = step.get("platform_id") or platform_id
    if step.get("scenario_id") and step.get("scenario_id") != scenario_id:
        _log(
            "Step scenario_id mismatch; using step value "
            f"step_scenario_id={step_scenario_id} grouped_scenario_id={scenario_id}"
        )
    if step.get("platform_id") and step.get("platform_id") != platform_id:
        _log(
            "Step platform_id mismatch; using step value "
            f"step_platform_id={step_platform_id} grouped_platform_id={platform_id}"
        )
    return step_scenario_id, step_platform_id
