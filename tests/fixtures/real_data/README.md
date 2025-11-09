# Real Data Testing Directory

## 📁 Purpose
This directory contains real CSV files for comprehensive validation testing.

## 📝 Instructions

### 1. Add Your CSV Files
Place your 20+ CSV files directly in this directory:
```
tests/fixtures/real_data/
├── file1.csv
├── file2.csv
├── file3.csv
└── ...
```

### 2. Run Validation
From the project root, run:
```bash
python validate_real_data_batch.py
```

### 3. Review Results
The script will generate:
- `VALIDATION_REPORT.md` - Detailed markdown report
- `validation_batch.log` - Detailed execution log
- Console output with real-time progress

## 📊 What Gets Tested
For each CSV file:
- ✅ All 10 metrics calculation
- ✅ Processing time
- ✅ Error handling
- ✅ Data quality issues
- ✅ Validation warnings
- ✅ Anomaly detection

## 📈 Report Includes
- Summary statistics (success rate, avg time)
- Performance stats (min/max/avg processing time)
- Metric statistics (step direction distribution, band entry rate, anomaly counts)
- Per-file detailed results
- Issues found (if any)

## 🧹 Cleanup
After validation is complete, you can:
1. Review the VALIDATION_REPORT.md
2. Delete this directory and files (temporary task)
3. Or keep for future reference

## 🔧 Expected File Format
CSV files should have these columns:
- `miner.seconds`
- `miner.mode.power`
- `miner.summary.wattage`
- `miner.temp.hash_board_max`
- `miner.psu.temp_max`
- `miner.outage`

The validation script will handle any data quality issues gracefully.

