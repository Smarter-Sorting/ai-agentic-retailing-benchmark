# Benchmark Report Viewer

Interactive web-based viewer for AI Agentic Retailing Benchmark reports.

## Features

### 📊 Interactive Filtering
- Filter by platform (ChatGPT, Claude, Gemini, etc.)
- Filter by ChatGPT tier (paid vs unpaid)
- Filter by scenario ID
- Real-time updates

### 📈 Statistics Dashboard
- Total test count
- Average accuracy scores
- Platform coverage
- Success rate metrics

### 🔍 Detailed Results View
- Comprehensive test results table
- Color-coded score indicators
- Platform badges
- Sortable columns

### 📉 Visual Comparisons
- Platform performance comparison
- Score distribution charts
- Tier comparison analysis (coming soon)

### 💾 Export Capabilities
- Export filtered results to JSON
- Share specific result subsets

## Getting Started

### Option 1: Direct Browser Open
```bash
# Open directly in your browser
open viewer/index.html  # macOS
xdg-open viewer/index.html  # Linux
start viewer/index.html  # Windows
```

### Option 2: Local HTTP Server
```bash
# Python 3
python -m http.server 8000

# Then visit: http://localhost:8000/viewer/
```

### Option 3: Node.js HTTP Server
```bash
npx http-server -p 8000
# Then visit: http://localhost:8000/viewer/
```

## Loading Data

### From JSON Reports
1. Generate JSON from your XLSX report:
   ```bash
   python generate_json_report.py reports/test_report_20250101_120000.xlsx
   ```

2. Click "Upload Report" in the viewer
3. Select your JSON file

### Sample Data
Click "Load Sample Data" to see the viewer in action with example results.

## Supported Formats

### JSON Format
```json
[
  {
    "scenario_id": "Q001",
    "platform_id": "CHATGPT",
    "tier": "paid",
    "step_id": "1",
    "step_index": "1",
    "identity_accuracy_score": "0.95",
    "attribute_completeness_score": "0.88",
    "attribute_correctness_score": "0.92",
    "step_outcome": "success",
    "comments": "Good performance"
  }
]
```

### XLSX Support
XLSX files require conversion to JSON:
```bash
python generate_json_report.py your_report.xlsx
```

## Browser Compatibility
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Opera 76+

## Future Enhancements
- [ ] Direct XLSX import (using SheetJS)
- [ ] Advanced chart visualizations (Chart.js integration)
- [ ] Export to PDF
- [ ] Compare multiple reports side-by-side
- [ ] Custom filter presets
- [ ] Performance trend analysis
- [ ] Automated report generation from CLI

## Technical Details

### Technologies Used
- Pure HTML/CSS/JavaScript (no build required)
- Responsive design for all screen sizes
- Modern ES6+ JavaScript
- CSS Grid and Flexbox layouts

### No Dependencies
The viewer runs entirely in the browser with no external dependencies for basic functionality. For advanced features (charts, XLSX parsing), optional libraries can be added:
- Chart.js for visualizations
- SheetJS for XLSX import

## Troubleshooting

### File Upload Not Working
- Ensure your JSON file is valid
- Check browser console for errors
- Try loading sample data first

### No Data Displaying
- Check that your JSON structure matches expected format
- Verify platform_id and score field names
- Use browser developer tools to inspect data

### Filters Not Working
- Reset filters and try again
- Ensure filter values match data exactly (case-sensitive)
- Check that data has been loaded successfully

## Contributing

Suggestions for improvements:
1. Open an issue describing the feature
2. Create a pull request with implementation
3. Include examples and documentation

## License

Same as parent project.
