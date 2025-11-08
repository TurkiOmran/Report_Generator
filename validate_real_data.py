"""Validation script for real CSV data"""
import sys
from pathlib import Path
import logging
import io

# Set UTF-8 encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from data_processing.ingestion import DataIngestion
from data_processing.preprocessing import DataPreprocessor

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)

def validate_csv(filepath: Path):
    """Validate a single CSV file through the complete pipeline"""
    print("\n" + "="*80)
    print(f"VALIDATING: {filepath.name}")
    print("="*80)
    
    try:
        # Step 1: Ingestion
        print("\n[1/2] INGESTION & VALIDATION")
        print("-" * 40)
        ingestion = DataIngestion()
        df, action_idx, warnings = ingestion.load_csv(filepath)
        
        print(f"✅ Successfully loaded {len(df)} rows")
        print(f"   Action index: {action_idx}")
        print(f"   Action time: {df.at[action_idx, 'seconds']:.2f}s")
        
        if warnings:
            print(f"\n⚠️  Warnings ({len(warnings)}):")
            for warning in warnings[:5]:  # Show first 5 warnings
                print(f"   - {warning}")
            if len(warnings) > 5:
                print(f"   ... and {len(warnings) - 5} more")
        
        # Step 2: Preprocessing
        print("\n[2/2] PREPROCESSING & ANALYSIS")
        print("-" * 40)
        preprocessor = DataPreprocessor(df, action_idx)
        df_processed, metadata = preprocessor.preprocess()
        
        print(f"✅ Preprocessing complete")
        print(f"\n{preprocessor.get_metadata_summary()}")
        
        # Show data sample
        print("\n" + "="*80)
        print("DATA SAMPLE (first 5 and last 5 rows)")
        print("="*80)
        print("\nFirst 5 rows:")
        print(df_processed[['seconds', 'mode_power', 'summary_wattage', 'outage']].head())
        print("\nLast 5 rows:")
        print(df_processed[['seconds', 'mode_power', 'summary_wattage', 'outage']].tail())
        
        return True, df_processed, metadata
        
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}")
        print(f"   {str(e)}")
        return False, None, None


def main():
    """Validate all real CSV files in tests/fixtures/"""
    fixtures_dir = Path(__file__).parent / "tests" / "fixtures"
    
    # Find all CSV files that look like real data (not our test fixtures)
    real_data_files = [
        f for f in fixtures_dir.glob("*.csv")
        if f.stem.startswith(('r2_', 'r6_', 'r9_', 'r10_'))  # Real data pattern
    ]
    
    if not real_data_files:
        print("❌ No real data CSV files found in tests/fixtures/")
        print("   Looking for files matching: r2_*.csv, r6_*.csv, r9_*.csv")
        return
    
    print(f"Found {len(real_data_files)} real data file(s) to validate\n")
    
    results = {}
    for csv_file in sorted(real_data_files):
        success, df, metadata = validate_csv(csv_file)
        results[csv_file.name] = success
    
    # Summary
    print("\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80)
    
    for filename, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {filename}")
    
    total = len(results)
    passed = sum(results.values())
    print(f"\nTotal: {passed}/{total} passed")
    
    if passed == total:
        print("\n🎉 All files validated successfully!")
        print("   Ready to use for metric calculations!")
    else:
        print(f"\n⚠️  {total - passed} file(s) failed validation")


if __name__ == "__main__":
    main()

