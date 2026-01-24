import argparse

from test_runner import run_tests


DEFAULT_DATASET = "retailing-benchmark"
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
        help="Optional platform_id to run (e.g. GEMINI).",
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


def main():
    args = _parse_args()
    dataset_config = _resolve_dataset_config(args.setting)
    run_tests(
        dataset_config["tests_xlsx"],
        env_path=args.env,
        platform_id=args.platform,
        scenario_start=args.scenario_start,
        scenario_end=args.scenario_end,
        ground_truth_path=dataset_config["ground_truth_xlsx"],
        scoring_prompt_path=dataset_config["scoring_prompt"],
    )


if __name__ == "__main__":
    main()
