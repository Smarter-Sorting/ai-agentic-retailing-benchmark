import os
from datetime import datetime

from report_xlsx import write_xlsx_report


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
]
OUTPUT_FIELDS = [
    "model_response",
    "full_model_response",
    "text_model_response",
    "comments",
    *SCORING_FIELDS,
]


def build_report_path(reports_dir="reports"):
    # Build a timestamped report path in the reports directory.
    os.makedirs(reports_dir, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return os.path.join(reports_dir, f"test_report_{timestamp}.xlsx")


def write_report(results, input_rows, reports_dir="reports", report_path=None):
    # Write an XLSX report with input columns and updated model outputs.
    os.makedirs(reports_dir, exist_ok=True)
    path = report_path or build_report_path(reports_dir)
    fieldnames = extract_fieldnames(input_rows, results)
    results_by_key = {result_key(row): row for row in results}
    rows = []
    for input_row in input_rows:
        row = dict(input_row)
        result = results_by_key.get(result_key(input_row))
        if result:
            for field in OUTPUT_FIELDS:
                if field in row or field in result:
                    row[field] = result.get(field, "")
        rows.append(row)
    if not input_rows and results:
        rows = [
            _build_result_row(row) for row in results
        ]
    write_xlsx_report(path, fieldnames, rows)
    return path


def format_scenario(row):
    # Format the scenario identifier as a pipe-delimited string.
    parts = [
        row.get("run_id", ""),
        row.get("scenario_id", ""),
        row.get("platform_id", ""),
        row.get("step_id", ""),
        row.get("step_index", ""),
        row.get("step_type", ""),
    ]
    return "|".join(str(part) for part in parts)


def result_key(row):
    # Build a stable key for matching input rows to results.
    return (
        row.get("run_id", ""),
        row.get("scenario_id", ""),
        row.get("platform_id", ""),
        row.get("step_id", ""),
        row.get("step_index", ""),
        row.get("step_type", ""),
    )


def extract_fieldnames(input_rows, results):
    # Pick output columns based on input rows, falling back to minimal fields.
    if input_rows:
        fieldnames = list(input_rows[0].keys())
        _append_missing_fields(fieldnames, results, OUTPUT_FIELDS)
        return fieldnames
    if results:
        fieldnames = ["scenario", "user_prompt"]
        fieldnames.extend(OUTPUT_FIELDS)
        _append_missing_fields(fieldnames, results, OUTPUT_FIELDS)
        return fieldnames
    return []


def _append_missing_fields(fieldnames, results, extra_fields):
    for field in extra_fields:
        if field in fieldnames:
            continue
        if any(field in row for row in results or []):
            fieldnames.append(field)


def _build_result_row(row):
    data = {
        "scenario": format_scenario(row),
        "user_prompt": row.get("user_prompt", ""),
    }
    for field in OUTPUT_FIELDS:
        data[field] = row.get(field, "")
    return data
