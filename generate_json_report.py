"""Generate JSON reports from XLSX files for the web viewer."""

import json
import os
import sys
from input_loader.test_loader import load_tests_xlsx


def generate_json_report(xlsx_path, output_path=None):
    """
    Convert an XLSX report to JSON format for the web viewer.
    
    Args:
        xlsx_path: Path to the XLSX report file
        output_path: Optional output path for JSON file
        
    Returns:
        Path to the generated JSON file
    """
    if not os.path.exists(xlsx_path):
        raise FileNotFoundError(f"XLSX file not found: {xlsx_path}")
    
    # Load the XLSX data
    rows = load_tests_xlsx(xlsx_path)
    
    # Generate output path if not provided
    if not output_path:
        base_name = os.path.splitext(xlsx_path)[0]
        output_path = f"{base_name}.json"
    
    # Write JSON file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
    
    print(f"Generated JSON report: {output_path}")
    print(f"Total rows: {len(rows)}")
    
    return output_path


def main():
    """CLI for generating JSON reports."""
    if len(sys.argv) < 2:
        print("Usage: python generate_json_report.py <xlsx_path> [output_path]")
        print("\nExample:")
        print("  python generate_json_report.py reports/test_report_20250101_120000.xlsx")
        sys.exit(1)
    
    xlsx_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        generate_json_report(xlsx_path, output_path)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
