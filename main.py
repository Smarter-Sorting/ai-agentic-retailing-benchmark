import argparse

from config import load_env_file
from test_runner import run_tests


DEFAULT_DATASET = "retailing-benchmark"
SCORING_PLATFORM_ENV_KEY = "SCORING_PLATFORM_ID"
DEFAULT_SCORING_PLATFORM_ID = "CHATGPT"
DATASET_CONFIGS = {
    "retailing-benchmark": {
        "tests_xlsx": "retailing-benchmark/shopping_paper_tests.xlsx",
        "ground_truth_xlsx": "retailing-benchmark/product_ground_truth.xlsx",
        "scoring_prompt": "retailing-benchmark/scoring_prompt.txt",
    }
}


def _resolve_dataset_config(dataset):
    dataset = (dataset or DEFAULT_DATASET).strip().lower()
    if dataset in DATASET_CONFIGS:
        return DATASET_CONFIGS[dataset]
    options = ", ".join(sorted(DATASET_CONFIGS.keys()))
    raise ValueError(f"Unknown dataset '{dataset}'. Available options: {options}")


def _parse_args():
    parser = argparse.ArgumentParser(description="Run tests.")
    parser.add_argument(
        "--setting",
        default="retailing-benchmark",
        help="Dataset setting name (maps to predefined input locations).",
    )
    parser.add_argument(
        "--env",
        default=".env",
        help="Path to the env file with platform credentials.",
    )
    parser.add_argument(
        "--platform",
        default=None,
        help="Optional platform_id(s) to run (e.g. GEMINI or GEMINI,CLAUDE).",
    )
    parser.add_argument(
        "--exclude-platform",
        default=None,
        help="Comma-separated platform_ids to exclude (e.g. GEMINI,CLAUDE).",
    )
    parser.add_argument(
        "--scenario-start",
        default=None,
        help="Optional scenario_id to start from (inclusive).",
    )
    parser.add_argument(
        "--scenario-end",
        default=None,
        help="Optional scenario_id to stop at (inclusive).",
    )
    return parser.parse_args()

def _resolve_scoring_platform_id(env):
    value = env.get(SCORING_PLATFORM_ENV_KEY, DEFAULT_SCORING_PLATFORM_ID)
    value = value.strip() if value else ""
    return value or DEFAULT_SCORING_PLATFORM_ID


def main():
    args = _parse_args()
    env = load_env_file(args.env)
    dataset_config = _resolve_dataset_config(args.setting)
    scoring_platform_id = _resolve_scoring_platform_id(env)
    included_platforms = _parse_platform_list(args.platform)
    excluded_platforms = _parse_platform_list(args.exclude_platform)
    run_tests(
        dataset_config["tests_xlsx"],
        env_path=args.env,
        platform_id=included_platforms,
        scenario_start=args.scenario_start,
        scenario_end=args.scenario_end,
        ground_truth_path=dataset_config.get("ground_truth_xlsx"),
        scoring_prompt_path=dataset_config.get("scoring_prompt"),
        scoring_platform_id=scoring_platform_id,
        excluded_platforms=excluded_platforms,
    )


def _parse_platform_list(value):
    if not value:
        return set()
    items = [item.strip().upper() for item in value.split(",")]
    return {item for item in items if item}


if __name__ == "__main__":
    main()
