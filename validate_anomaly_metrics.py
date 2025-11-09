"""
Validation script for Anomaly and Plateau Metrics (METRIC 7 and METRIC 8).

Tests the implemented metrics against real CSV data to verify behavior.
"""

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
from metrics.basic_metrics import BasicMetrics
from metrics.time_metrics import TimeMetrics
from metrics.anomaly_metrics import AnomalyMetrics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)


def validate_metrics_on_file(filepath: Path) -> bool:
    """Validate METRIC 7 and METRIC 8 on a single CSV file."""
    print(f"\n{'='*80}\nTESTING: {filepath.name}\n{'='*80}\n")
    try:
        # Load and preprocess data
        ingestion = DataIngestion()
        df, action_idx, warnings = ingestion.load_csv(filepath)
        
        print(f"✅ Data loaded: {len(df)} rows, action at index {action_idx}")
        
        preprocessor = DataPreprocessor(df, action_idx)
        preprocessor.preprocess()
        
        print(f"✅ Preprocessing complete")
        
        # Calculate basic metrics (needed for context)
        basic_metrics = BasicMetrics(df, action_idx)
        target_power = basic_metrics.calculate_target_power()
        
        print(f"\n{'─'*80}\nContext\n{'─'*80}")
        print(f"  Target After:     {target_power['after']:.2f}W")
        
        # Initialize metrics calculators
        time_metrics = TimeMetrics(df, action_idx)
        anomaly_metrics = AnomalyMetrics(df, action_idx)
        
        # METRIC 7: Stable Plateau Duration
        print(f"\n{'─'*80}\nMETRIC 7: Stable Plateau Duration (±20W Tolerance)\n{'─'*80}")
        
        plateau = time_metrics.calculate_plateau_duration(target_power)
        
        summary = plateau['summary']
        print(f"  Total Plateaus:   {summary['total_count']}")
        print(f"  Longest Duration: {summary['longest_duration']:.1f}s")
        print(f"  Total Stable Time: {summary['total_stable_time']:.1f}s")
        
        if plateau['plateaus']:
            print(f"\n  Plateau Details:")
            for i, plat in enumerate(plateau['plateaus'][:3], 1):  # Show first 3
                print(f"    {i}. t={plat['start_time']:.1f}s, duration={plat['duration']:.1f}s, "
                      f"avg={plat['avg_wattage']:.0f}W")
                print(f"       exit: {plat['exit_reason']} at t={plat['exit_time']:.1f}s")
            if len(plateau['plateaus']) > 3:
                print(f"    ... and {len(plateau['plateaus']) - 3} more")
            
            # Validate plateaus
            all_valid = True
            for plat in plateau['plateaus']:
                if plat['duration'] < 30.0:
                    print(f"  ⚠️  Plateau duration {plat['duration']:.1f}s < 30s minimum")
                    all_valid = False
                if abs(plat['avg_wattage'] - target_power['after']) > 20.0:
                    print(f"  ⚠️  Avg wattage {plat['avg_wattage']:.0f}W outside ±20W tolerance")
                    all_valid = False
            
            if all_valid:
                print(f"  ✅ All plateaus meet criteria (≥30s, ±20W)")
        else:
            print(f"  ⚠️  No stable plateaus detected (none ≥30s within ±20W)")
        
        # METRIC 8: Sharp Drops
        print(f"\n{'─'*80}\nMETRIC 8: Sharp Drops (15% Threshold, 5s Window)\n{'─'*80}")
        
        drops = anomaly_metrics.calculate_sharp_drops()
        
        drop_summary = drops['summary']
        print(f"  Total Drops:      {drop_summary['count']}")
        
        if drop_summary['worst_magnitude'] is not None:
            print(f"  Worst Magnitude:  {drop_summary['worst_magnitude']:.0f}W")
            print(f"  Worst Rate:       {drop_summary['worst_rate']:.1f} W/s")
        
        if drops['sharp_drops']:
            print(f"\n  Drop Details:")
            for i, drop in enumerate(drops['sharp_drops'][:5], 1):  # Show first 5
                pct = (drop['magnitude'] / drop['start_wattage']) * 100
                print(f"    {i}. t={drop['time']:.1f}s: {drop['start_wattage']:.0f}W → {drop['end_wattage']:.0f}W")
                print(f"       magnitude={drop['magnitude']:.0f}W ({pct:.1f}%), "
                      f"duration={drop['duration']:.2f}s, rate={drop['rate']:.1f}W/s")
            if len(drops['sharp_drops']) > 5:
                print(f"    ... and {len(drops['sharp_drops']) - 5} more")
            
            # Validate drops
            all_valid = True
            for drop in drops['sharp_drops']:
                drop_pct = drop['magnitude'] / drop['start_wattage']
                if drop_pct < 0.15:
                    print(f"  ⚠️  Drop at t={drop['time']:.1f}s below 15% threshold ({drop_pct*100:.1f}%)")
                    all_valid = False
                if drop['duration'] > 5.0:
                    print(f"  ⚠️  Drop duration {drop['duration']:.1f}s exceeds 5s window")
                    all_valid = False
                if drop['rate'] >= 0:
                    print(f"  ⚠️  Drop rate {drop['rate']:.1f} is not negative")
                    all_valid = False
            
            if all_valid:
                print(f"  ✅ All drops meet criteria (≥15%, ≤5s window, negative rate)")
        else:
            print(f"  ✅ No sharp drops detected (clean power profile)")
        
        # Cross-metric analysis
        print(f"\n{'─'*80}\nCross-Metric Analysis\n{'─'*80}")
        
        if plateau['summary']['total_count'] > 0 and drop_summary['count'] > 0:
            print(f"  ⚠️  Has both plateaus and sharp drops (mixed stability)")
        elif plateau['summary']['total_count'] > 0:
            print(f"  ✅ Stable operation detected without sharp drops")
        elif drop_summary['count'] > 0:
            print(f"  ⚠️  Unstable operation with sharp drops but no sustained plateaus")
        else:
            print(f"  ⚠️  Neither plateaus nor sharp drops detected")
        
        # Quality score
        if plateau['summary']['total_stable_time'] > 0:
            total_test_time = df[df['seconds'] >= 0]['seconds'].max()
            stability_pct = (plateau['summary']['total_stable_time'] / total_test_time) * 100
            print(f"  Stability:        {stability_pct:.1f}% of test time")
        
        print(f"\n✅ Metrics calculated successfully for {filepath.name}\n")
        return True
        
    except Exception as e:
        print(f"❌ Error processing {filepath.name}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main validation routine."""
    fixtures_dir = Path("tests/fixtures")
    
    if not fixtures_dir.exists():
        print(f"❌ Fixtures directory not found: {fixtures_dir}")
        return 1
    
    # Find all CSV files
    csv_files = sorted(fixtures_dir.glob("*.csv"))
    
    if not csv_files:
        print(f"❌ No CSV files found in {fixtures_dir}")
        return 1
    
    print(f"Found {len(csv_files)} CSV file(s) to validate\n")
    
    results = []
    for csv_file in csv_files:
        success = validate_metrics_on_file(csv_file)
        results.append((csv_file.name, success))
    
    # Summary
    print(f"\n{'='*80}\nVALIDATION SUMMARY\n{'='*80}\n")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for filename, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} - {filename}")
    
    print(f"\nTotal: {passed}/{total} files validated successfully")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())


