# shopping-paper-qa

Minimal runner for executing shopping-paper test scenarios against multiple AI platforms and saving a timestamped report.

## Requirements
- Python 3.9+ (standard library only; no external dependencies for REST platforms)
- Optional for GEMINI: `pip install -q -U google-genai`

## Running Tests
Run all scenarios in `input_data/shopping_paper_tests.xlsx` and write a report:

```bash
python - <<'PY'
from shopping_paper_test_runner import run_tests

run_tests("input_data/shopping_paper_tests.xlsx")
PY
```

Or use the CLI:

```bash
python shopping_paper_test_runner.py --xlsx input_data/shopping_paper_tests.xlsx --env .env
```

Run only tests for a specific platform_id (case-insensitive):

```bash
python shopping_paper_test_runner.py --xlsx input_data/shopping_paper_tests.xlsx --env .env --platform GEMINI
```

Run only a range of scenarios (inclusive):

```bash
python shopping_paper_test_runner.py --xlsx input_data/shopping_paper_tests.xlsx --env .env --scenario-start 10 --scenario-end 20
```

By default, reports are written to `reports/` with a timestamped filename like:
`reports/test_report_20250101_120000.xlsx`

## Notes
- Scenarios are grouped by `scenario_id` and `platform_id`, and steps are executed in `step_index` order.
- The report preserves the input XLSX columns and fills `full_model_response` and
  `text_model_response` with the latest run outputs.
 - Reports are updated after each step to preserve partial progress if a run fails.
