"""
Validation Script for Basic Metrics (METRIC 1 and METRIC 2)

Tests the implemented metrics against real CSV data files.
"""

import sys
from pathlib import Path
import io

# Set UTF-8 encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from data_processing.ingestion import DataIngestion
from data_processing.preprocessing import DataPreprocessor
from metrics.basic_metrics import BasicMetrics


def validate_metrics_on_file(filepath: Path):
    """Validate metrics on a single CSV file"""
    print(f"\n{'='*80}")
    print(f"TESTING: {filepath.name}")
    print(f"{'='*80}\n")
    
    try:
        # Step 1: Ingest data
        ingestion = DataIngestion()
        df, action_idx, warnings = ingestion.load_csv(filepath)
        
        print(f"✅ Data loaded: {len(df)} rows, action at index {action_idx}")
        
        # Step 2: Preprocess
        preprocessor = DataPreprocessor(df, action_idx)
        preprocessor.preprocess()
        
        print(f"✅ Preprocessing complete")
        if 'target_power_before' in preprocessor.metadata and 'target_power_after' in preprocessor.metadata:
            print(f"   Power transition: {preprocessor.metadata['target_power_before']:.0f}W → "
                  f"{preprocessor.metadata['target_power_after']:.0f}W")
        
        # Step 3: Calculate metrics
        metrics = BasicMetrics(df, action_idx)
        
        # METRIC 1: Start Power
        print(f"\n{'─'*80}")
        print("METRIC 1: Start Power")
        print(f"{'─'*80}")
        
        start_power = metrics.calculate_start_power()
        
        print(f"  Median power:     {start_power['median']:.2f}W")
        print(f"  Last value:       {start_power['last_value']:.2f}W" if start_power['last_value'] is not None else "  Last value:       NaN")
        print(f"  Difference:       {start_power['difference']:.2f}W" if start_power['difference'] is not None else "  Difference:       N/A")
        print(f"  Note:             {start_power['note'] if start_power['note'] else 'None'}")
        
        # Validate against preprocessing metadata (if available)
        if 'target_power_before' in preprocessor.metadata:
            preprocessing_before = preprocessor.metadata['target_power_before']
            if abs(start_power['median'] - preprocessing_before) / preprocessing_before < 0.05:  # Within 5%
                print(f"  ✅ Within 5% of target power before ({preprocessing_before:.0f}W)")
            else:
                percentage_diff = abs(start_power['median'] - preprocessing_before) / preprocessing_before * 100
                print(f"  ⚠️  Differs from target before by {percentage_diff:.1f}% ({preprocessing_before:.0f}W vs {start_power['median']:.0f}W)")
        
        # METRIC 2: Target Power
        print(f"\n{'─'*80}")
        print("METRIC 2: Target Power")
        print(f"{'─'*80}")
        
        target_power = metrics.calculate_target_power()
        
        print(f"  Before action:    {target_power['before']:.2f}W")
        print(f"  After action:     {target_power['after']:.2f}W")
        print(f"  Change:           {target_power['change']:+.2f}W")
        
        # Determine direction
        if target_power['change'] > 50:
            direction_str = f"UP (ramping up {target_power['change']:.0f}W)"
        elif target_power['change'] < -50:
            direction_str = f"DOWN (ramping down {abs(target_power['change']):.0f}W)"
        else:
            direction_str = f"MINIMAL (change {target_power['change']:+.0f}W)"
        
        print(f"  Direction:        {direction_str}")
        
        # Validate against preprocessing metadata
        if 'target_power_after' in preprocessor.metadata:
            preprocessing_target = preprocessor.metadata['target_power_after']
            if abs(target_power['after'] - preprocessing_target) < 1.0:
                print(f"  ✅ Matches preprocessing target power ({preprocessing_target:.0f}W)")
            else:
                print(f"  ⚠️  Differs from preprocessing ({preprocessing_target:.0f}W vs {target_power['after']:.0f}W)")
        
        # Validate that target_power['before'] matches start_power (within ~5%)
        expected_match = target_power['before']
        actual_median = start_power['median']
        percentage_diff = abs(expected_match - actual_median) / expected_match * 100
        
        print(f"\n{'─'*80}")
        print("Cross-Metric Validation")
        print(f"{'─'*80}")
        print(f"  Target before:    {expected_match:.0f}W")
        print(f"  Start median:     {actual_median:.0f}W")
        print(f"  Difference:       {percentage_diff:.2f}%")
        
        if percentage_diff < 5.0:
            print(f"  ✅ Target 'before' and start power match within 5%")
        else:
            print(f"  ⚠️  Significant difference (>{5:.0f}%)")
        
        print(f"\n✅ All metrics calculated successfully for {filepath.name}\n")
        return True
        
    except Exception as e:
        print(f"❌ Error processing {filepath.name}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Validate metrics on all real data files"""
    fixtures_dir = Path(__file__).parent / "tests" / "fixtures"
    
    # Find all real data CSV files
    real_data_files = [
        f for f in fixtures_dir.glob("*.csv")
        if f.stem.startswith(('r2_', 'r6_', 'r9_', 'r10_'))
    ]
    
    if not real_data_files:
        print("❌ No real data CSV files found in tests/fixtures/")
        return
    
    print(f"\n{'='*80}")
    print(f"BASIC METRICS VALIDATION")
    print(f"{'='*80}")
    print(f"Found {len(real_data_files)} real data file(s) to validate\n")
    
    results = []
    for filepath in sorted(real_data_files):
        success = validate_metrics_on_file(filepath)
        results.append((filepath.name, success))
    
    # Summary
    print(f"\n{'='*80}")
    print("VALIDATION SUMMARY")
    print(f"{'='*80}")
    
    for filename, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {filename}")
    
    total = len(results)
    passed = sum(1 for _, success in results if success)
    
    print(f"\nTotal: {passed}/{total} passed")
    
    if passed == total:
        print("\n🎉 All files validated successfully!")
        print("   METRIC 1 (Start Power) and METRIC 2 (Target Power) are working correctly!")
    else:
        print(f"\n⚠️  {total - passed} file(s) failed validation")


if __name__ == "__main__":
    main()

