# Project Organization Guide

This document explains the organization of the Power Profile Report Generator project.

## 📁 Root Directory (Clean & Essential)

```
Report_Generator/
├── README.md                                    # Project overview and setup
├── requirements.txt                             # Python dependencies
├── pytest.ini                                   # Test configuration
├── R_Test_Metrics_Complete_Pseudocode_v3.md    # Metric algorithm reference
├── test_single_report.py                        # Demo script (run this to see the project in action!)
├── src/                                         # Source code
├── tests/                                       # Test suite
├── test_reports/                                # Generated HTML reports
├── docs/                                        # Documentation
└── venv/                                        # Virtual environment
```

## 📚 Documentation Structure (`docs/`)

### Main Documentation
- **CLAUDE.md** - Claude AI integration notes
- **phase1_report_structure_reference.md** - Report structure specification
- **prd.txt** - Product Requirements Document
- **prompt.txt** - Development prompts
- **SETUP.md** - Setup instructions

### Completed Tasks (`docs/completed_tasks/`)
Historical completion summaries for each implemented task:
- **TASK4_COMPLETION_SUMMARY.md** - Basic Metrics (Start Power, Target Power)
- **TASK6_COMPLETION_SUMMARY.md** - Band Entry Metric
- **TASK7_COMPLETION_SUMMARY.md** - Setpoint Hit Metric
- **TASK8_COMPLETION_SUMMARY.md** - Stable Plateau Metric
- **TASK9_COMPLETION_SUMMARY.md** - Sharp Drops/Rises Metrics
- **TASK10_COMPLETION_SUMMARY.md** - Overshoot/Undershoot Metric
- **TASK14_COMPLETION_SUMMARY.md** - HTML Report Generation
- **TASK15_PROGRESS_SUMMARY.md** - End-to-End Pipeline Orchestration

### Feature Documentation (`docs/features/`)
Detailed documentation for major features:
- **EXPANDABLE_DETAILS_FEATURE.md** - Interactive expandable metric details in reports
- **PHASE1_REFERENCE_COMPLIANCE_REPORT.md** - Verification that all Phase 1 specs are implemented

## 🎯 Quick Start

**To see the project in action:**
```bash
python test_single_report.py
```

This will:
1. Process a sample CSV file
2. Calculate all 10 metrics
3. Generate an interactive visualization
4. Create Claude AI analysis (if API key configured)
5. Export a complete HTML report

**Generated report location:** `test_reports/report_<timestamp>.html`

## 🧪 Running Tests

```bash
# Run all tests
pytest

# Run specific test suite
pytest tests/test_metrics/           # Metric calculations
pytest tests/test_pipeline/          # End-to-end pipeline
pytest tests/test_reporting/         # HTML generation

# Run with coverage
pytest --cov=src
```

## 📊 Project Structure

### Source Code (`src/`)
- **analysis/** - Claude AI integration for narrative analysis
- **data_processing/** - CSV ingestion, validation, preprocessing
- **metrics/** - All 10 metrics calculation functions
- **pipeline/** - End-to-end report generation orchestration
- **reporting/** - HTML generation, formatting, file export
- **visualization/** - Plotly chart generation

### Tests (`tests/`)
- **test_analysis/** - AI analysis tests
- **test_data_processing/** - Data pipeline tests
- **test_metrics/** - Metric calculation tests
- **test_pipeline/** - Integration tests
- **test_reporting/** - Report generation tests
- **test_visualization/** - Chart generation tests
- **fixtures/** - Test CSV files and sample data

## 🎨 Generated Reports

All reports include:
- ✅ Test metadata (file info, test type, duration)
- ✅ 10 calculated metrics with expandable details
- ✅ Interactive Plotly power timeline chart
- ✅ Claude AI narrative analysis (optional)
- ✅ Self-contained HTML (no external dependencies)

**Report sections:**
1. Test Information
2. Performance Metrics (Basic, Time-Based, Anomaly Detection)
3. Power Timeline (Interactive Chart)
4. AI Analysis (Claude-generated insights)

## 🔧 Configuration

- **Environment Variables:** `.env` (API keys, see `.env.example`)
- **Python Dependencies:** `requirements.txt`
- **Test Configuration:** `pytest.ini`

## 📖 Further Reading

- See `docs/completed_tasks/` for implementation history
- See `docs/features/` for feature specifications
- See `R_Test_Metrics_Complete_Pseudocode_v3.md` for metric algorithms
- See `docs/phase1_report_structure_reference.md` for report structure

---

**Last Updated:** November 11, 2025  
**Project Status:** ✅ Phase 1 Complete, Phase 2 Complete, Production Ready

