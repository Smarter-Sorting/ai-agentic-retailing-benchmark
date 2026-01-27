# ai-agentic-retailing-benchmark

Minimal runner for executing ai-agentic-retailing-benchmark test scenarios against multiple AI platforms and saving a timestamped report.

## Requirements
- Python 3.9+ (standard library only; no external dependencies for REST platforms)
- Optional for GEMINI: `pip install -q -U google-genai`

## Running Tests
Run all scenarios in the default dataset setting and write a report:

```bash
python - <<'PY'
from test_runner import run_tests

run_tests()
PY
```

Or use the CLI:

```bash
python main.py --setting retailing-benchmark --env .env
```

CLI parameters:
- `--setting`: Dataset setting name that selects a bundle of inputs (tests XLSX, ground truth, scoring prompt). Default: `retailing-benchmark`.
- `--env`: Path to the env file with platform credentials. Default: `.env`.
- `--platform`: Optional platform id(s) to run (e.g. `GEMINI` or `GEMINI,CLAUDE`). Case-insensitive.
- `--exclude-platform`: Optional comma-separated platform ids to skip (e.g. `GEMINI,CLAUDE`).
- `--scenario-start`: Optional scenario_id to start from (inclusive).
- `--scenario-end`: Optional scenario_id to stop at (inclusive).

Run only tests for a specific platform_id (case-insensitive):

```bash
python main.py --setting retailing-benchmark --env .env --platform GEMINI
```

Run only a range of scenarios (inclusive):

```bash
python main.py --setting retailing-benchmark --env .env --scenario-start 10 --scenario-end 20
```

By default, reports are written to `reports/` with a timestamped filename like:
`reports/test_report_20250101_120000.xlsx`

## Docker
Build the image:

```bash
docker build -t ai-agentic-retailing-benchmark .
```

Run with auto-start (default `CMD` runs `main.py`):

```bash
docker run --rm -v "$PWD/.env:/app/.env" ai-agentic-retailing-benchmark
```

Store reports inside the container and fetch them later:

```bash
docker ps
docker exec -it <container_id> /bin/bash
ls /app/reports
```

Store reports on the host by mounting the reports directory:

```bash
mkdir -p reports
docker run --rm -v "$PWD/.env:/app/.env" -v "$PWD/reports:/app/reports" ai-agentic-retailing-benchmark
```

Override the default command (example: run a different setting):

```bash
docker run --rm -v "$PWD/.env:/app/.env" ai-agentic-retailing-benchmark python main.py --setting retailing-benchmark --env .env --platform GEMINI
```

## Project Structure
- `main.py`: CLI entrypoint for running tests.
- `test_runner.py`: Test runner logic (grouping, execution, scoring, reporting).
- `platform_clients.py`: Platform-specific API calls for each model/provider.
- `config.py`: Loads env values and platform configuration.
- `input_loader/`: Input loading utilities.
- `input_loader/test_loader.py`: XLSX test case loader.
- `input_loader/product_ground_truth_loader.py`: Product ground truth loader.
- `reporter/`: Reporting package.
- `reporter/reporting.py`: Report assembly and XLSX writing orchestration.
- `reporter/report_xlsx.py`: Low-level XLSX writer.
- `retailing-benchmark/`: Test inputs and prompts for the retailing benchmark setting.
- `retailing-benchmark/shopping_paper_tests.xlsx`: Test scenarios and steps.
- `retailing-benchmark/product_ground_truth.xlsx`: Product ground truth data.
- `retailing-benchmark/scoring_prompt.txt`: Scoring prompt template.
- `reports/`: Output reports (timestamped XLSX files).
- `results/`: Benchmark artifacts (paper + scored XLSX) for 100 multi-step scenarios across common models.
- `.env`: Platform credentials (not committed).

## Dataset Settings
Settings let you switch between different input bundles without changing CLI flags. The mapping
lives in `main.py` under `DATASET_CONFIGS`.

To add a new setting:
1) Create a new folder with your inputs (tests XLSX, optional ground truth XLSX, optional scoring prompt).
2) Add a new entry in `DATASET_CONFIGS` with the three file paths.
3) Run with `--setting your-setting-name`.

## Notes
- Scoring is skipped if the scoring prompt or ground truth file is missing for the selected setting.
- API or model call failures are captured in the `comments` column for the affected test step.
- Scenarios are grouped by `scenario_id` and `platform_id`, and steps are executed in `step_index` order.
- The report preserves the input XLSX columns and fills `full_model_response` and
  `text_model_response` with the latest run outputs.
 - Reports are updated after each step to preserve partial progress if a run fails.
