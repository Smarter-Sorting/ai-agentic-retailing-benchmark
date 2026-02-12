# Getting Started with Phase 2 Features

This guide walks you through using all the new features added in Phase 2 of the benchmark suite.

## 1. Browser-Based Testing (Foundation)

The browser testing module provides the foundation for browser-driven test scenarios:

```python
from browser_testing.browser_client import BrowserTestClient

# Initialize browser test client
client = BrowserTestClient(headless=True, timeout=30)

# Execute browser-based tests
results = client.execute_browser_test(
    platform_id="CHATGPT",
    scenario_steps=steps,
    config=config
)

client.close()
```

**Note:** Full browser automation requires Playwright or Selenium installation:
```bash
pip install playwright
playwright install chromium
```

## 2. ChatGPT Tier Comparison Testing

Compare performance between paid and unpaid ChatGPT accounts:

### Setup
Edit your `.env` file:
```bash
# For paid ChatGPT Plus/Pro account
CHATGPT_BASE_URL=https://api.openai.com/v1/chat/completions
CHATGPT_API_KEY=your-api-key
CHATGPT_MODEL=gpt-4
CHATGPT_TIER=paid

# For unpaid account (separate .env or run)
CHATGPT_TIER=unpaid
```

### Run Tests
```bash
# Test with paid tier
python main.py --setting retailing-benchmark --env .env.paid --platform CHATGPT

# Test with unpaid tier  
python main.py --setting retailing-benchmark --env .env.unpaid --platform CHATGPT
```

### Analyze Results
The tier information is captured in reports and can be filtered in the viewer.

## 3. Electronics Deep Dive Dataset

Run focused tests on electronics products:

### Run Electronics Tests
```bash
python main.py --setting electronics-deep-dive --env .env
```

### Dataset Structure
```
electronics-deep-dive/
├── README.md                           # Dataset documentation
├── electronics_tests.xlsx              # Test scenarios (create this)
├── electronics_ground_truth.xlsx       # Product data (create this)
└── electronics_scoring_prompt.txt      # Scoring criteria (included)
```

### Creating Electronics Test Data
1. Copy structure from `retailing-benchmark/shopping_paper_tests.xlsx`
2. Focus on electronics products (laptops, phones, TVs, etc.)
3. Include technical specification queries
4. Test regulatory compliance questions

### Example Scenarios
- "Compare the processor performance of these two laptops..."
- "What's the difference between OLED and QLED TVs?"
- "Does this phone support 5G connectivity?"
- "What safety certifications does this device have?"

## 4. Interactive Report Viewer

Visualize and analyze benchmark results:

### Quick Start
```bash
# 1. Run tests and generate reports
python main.py --setting retailing-benchmark --env .env

# 2. Convert XLSX report to JSON
python generate_json_report.py reports/test_report_20250212_150000.xlsx

# 3. Start web server
python -m http.server 8000

# 4. Open browser
# Navigate to: http://localhost:8000/viewer/
```

### Using the Viewer

#### Load Data
- Click "Upload Report" and select your JSON file
- Or click "Load Sample Data" to see a demo

#### Filter Results
- **Platform**: Choose specific AI platform (ChatGPT, Claude, etc.)
- **Tier**: Filter by ChatGPT tier (paid/unpaid)
- **Scenario**: Enter scenario ID to filter

#### Analyze Results
- **Statistics Cards**: View key metrics at a glance
- **Results Table**: Detailed test results with color-coded scores
  - Green (≥80%): High performance
  - Yellow (60-79%): Medium performance
  - Red (<60%): Low performance
- **Platform Comparison**: Visual comparison across platforms
- **Score Distribution**: Score patterns and trends

#### Export Data
- Click "Export Filtered Results" to save filtered data as JSON
- Share specific result subsets with team members

## 5. Complete Workflow Example

Here's a complete workflow using all Phase 2 features:

```bash
# Step 1: Set up environment for tier testing
cat > .env.paid <<EOF
CHATGPT_BASE_URL=https://api.openai.com/v1/chat/completions
CHATGPT_API_KEY=your-paid-api-key
CHATGPT_MODEL=gpt-4
CHATGPT_TIER=paid
CLAUDE_BASE_URL=https://api.anthropic.com/v1/messages
CLAUDE_API_KEY=your-claude-key
CLAUDE_MODEL=claude-3-opus-20240229
EOF

cat > .env.unpaid <<EOF
CHATGPT_BASE_URL=https://api.openai.com/v1/chat/completions
CHATGPT_API_KEY=your-unpaid-api-key
CHATGPT_MODEL=gpt-3.5-turbo
CHATGPT_TIER=unpaid
EOF

# Step 2: Run comprehensive tests
python main.py --setting retailing-benchmark --env .env.paid --platform CHATGPT
python main.py --setting retailing-benchmark --env .env.unpaid --platform CHATGPT
python main.py --setting electronics-deep-dive --env .env.paid

# Step 3: Convert reports to JSON
python generate_json_report.py reports/test_report_20250212_150000.xlsx
python generate_json_report.py reports/test_report_20250212_150100.xlsx
python generate_json_report.py reports/test_report_20250212_150200.xlsx

# Step 4: Analyze in viewer
python -m http.server 8000
# Open http://localhost:8000/viewer/
# Load each report and compare results
```

## 6. Advanced Usage

### Combining Filters
Filter by multiple criteria simultaneously:
1. Select platform: "ChatGPT"
2. Select tier: "paid"
3. Enter scenario: "Q001"
Result: Only paid ChatGPT tests for scenario Q001

### Comparative Analysis
1. Load first report (paid tier results)
2. Export filtered results
3. Load second report (unpaid tier results)
4. Export filtered results
5. Compare JSON files programmatically

### Custom Visualizations
The viewer's JavaScript is modular. Add custom charts by:
1. Including Chart.js library
2. Modifying `updateCharts()` function
3. Adding new chart containers to HTML

## 7. Troubleshooting

### Issue: Browser tests show "pending" status
**Solution:** Install Playwright or Selenium:
```bash
pip install playwright
playwright install chromium
```

### Issue: Tier not showing in results
**Solution:** Ensure `CHATGPT_TIER` is set in `.env` file before running tests

### Issue: Viewer not loading JSON
**Solution:** 
- Verify JSON is valid (use `jq` or JSON validator)
- Check browser console for errors
- Ensure file path is correct

### Issue: Charts not displaying
**Solution:** Charts require Chart.js library (optional). The viewer works without it.

## 8. Next Steps

### Enhance Browser Testing
Add Playwright integration:
```python
from playwright.sync_api import sync_playwright

def execute_browser_test(platform_id, steps, config):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        # Navigate and interact
        browser.close()
```

### Add More Datasets
Create category-specific datasets:
- `fashion-deep-dive/`
- `home-appliances-deep-dive/`
- `books-deep-dive/`

### Enhance Viewer
- Add Chart.js for visualizations
- Implement XLSX direct import
- Add PDF export
- Create comparison mode for multiple reports

## Support

For issues or questions:
1. Check existing documentation
2. Review example configurations
3. Open an issue on GitHub
4. Contact the development team

## Contributing

To add new features:
1. Follow the existing code patterns
2. Add documentation
3. Include usage examples
4. Update this guide
5. Submit a pull request
