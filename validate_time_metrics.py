"""
Validation script for Time Metrics (METRIC 5 and METRIC 6).

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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)


def validate_metrics_on_file(filepath: Path) -> bool:
    """Validate METRIC 5 and METRIC 6 on a single CSV file."""
    print(f"\n{'='*80}\nTESTING: {filepath.name}\n{'='*80}\n")
    try:
        # Load and preprocess data
        ingestion = DataIngestion()
        df, action_idx, warnings = ingestion.load_csv(filepath)
        
        print(f"✅ Data loaded: {len(df)} rows, action at index {action_idx}")
        
        preprocessor = DataPreprocessor(df, action_idx)
        preprocessor.preprocess()
        
        print(f"✅ Preprocessing complete")
        
        # Calculate basic metrics (needed for time metrics)
        basic_metrics = BasicMetrics(df, action_idx)
        
        start_power = basic_metrics.calculate_start_power()
        target_power = basic_metrics.calculate_target_power()
        step_direction = basic_metrics.calculate_step_direction(start_power, target_power)
        
        print(f"\n{'─'*80}\nBasic Metrics (for reference)\n{'─'*80}")
        print(f"  Start Power:      {start_power['median']:.2f}W")
        print(f"  Target Before:    {target_power['before']:.2f}W")
        print(f"  Target After:     {target_power['after']:.2f}W")
        print(f"  Step Direction:   {step_direction['direction']} ({step_direction['delta']:+.0f}W)")
        
        # Calculate time metrics
        time_metrics = TimeMetrics(df, action_idx)
        
        # METRIC 5: Band Entry
        print(f"\n{'─'*80}\nMETRIC 5: Band Entry (Adaptive Tolerance)\n{'─'*80}")
        
        band_entry = time_metrics.calculate_band_entry(target_power, start_power, step_direction)
        
        print(f"  Status:           {band_entry['status']}")
        
        if 'band_limits' in band_entry:
            limits = band_entry['band_limits']
            print(f"  Band Range:       {limits['lower']:.0f}W - {limits['upper']:.0f}W")
            print(f"  Tolerance:        ±{limits['tolerance']:.0f}W")
            
            # Calculate what % of target the tolerance is
            tolerance_pct = (limits['tolerance'] / target_power['after']) * 100
            print(f"  Tolerance %:      {tolerance_pct:.1f}% of target")
        
        if band_entry['status'] == 'ENTERED':
            print(f"  Entry Time:       {band_entry['time']:.1f}s")
            print(f"  Entry Wattage:    {band_entry['wattage']:.0f}W")
            print(f"  Entry %:          {band_entry['percentage']:.1f}% of target")
            if band_entry['entry_method']:
                print(f"  Entry Method:     {band_entry['entry_method']}")
                
        elif band_entry['status'] == 'INITIALLY_IN_BAND':
            print(f"  ✓ Already in band at t=0")
            print(f"  Entry Wattage:    {band_entry['wattage']:.0f}W")
            
        elif band_entry['status'] == 'BRIEF_ENTRY_NOT_SUSTAINED':
            print(f"  ⚠️  Entered briefly at {band_entry['time']:.1f}s but didn't sustain for 15s")
            print(f"  Duration:         {band_entry['duration']:.1f}s")
            
        elif band_entry['status'] == 'NOT_ENTERED':
            if 'closest_approach' in band_entry:
                closest = band_entry['closest_approach']
                print(f"  ❌ Never entered band")
                print(f"  Closest:          {closest['wattage']:.0f}W at {closest['time']:.1f}s")
                print(f"  Distance:         {closest['distance']:.0f}W from target")
        
        # METRIC 6: Setpoint Hit
        print(f"\n{'─'*80}\nMETRIC 6: Setpoint Hit (±30W Tolerance)\n{'─'*80}")
        
        setpoint_hit = time_metrics.calculate_setpoint_hit(target_power)
        
        summary = setpoint_hit['summary']
        print(f"  Brief Touches:    {summary['total_brief_touches']}")
        print(f"  Sustained Hits:   {summary['total_sustained_hits']}")
        
        if summary['first_sustained_hit_time'] is not None:
            print(f"  First Sustained:  {summary['first_sustained_hit_time']:.1f}s")
            print(f"  ✓ Achieved sustained hit (≥25s)")
        else:
            if summary['never_sustained']:
                print(f"  ⚠️  Never sustained within ±30W for 25s")
        
        # Show details of brief touches
        if setpoint_hit['brief_touches']:
            print(f"\n  Brief Touches Detail:")
            for i, touch in enumerate(setpoint_hit['brief_touches'][:3], 1):  # Show first 3
                print(f"    {i}. t={touch['time']:.1f}s, {touch['wattage']:.0f}W, "
                      f"duration={touch['duration']:.1f}s, exit: {touch['exit_reason']}")
            if len(setpoint_hit['brief_touches']) > 3:
                print(f"    ... and {len(setpoint_hit['brief_touches']) - 3} more")
        
        # Show details of sustained hits
        if setpoint_hit['sustained_hits']:
            print(f"\n  Sustained Hits Detail:")
            for i, hit in enumerate(setpoint_hit['sustained_hits'], 1):
                print(f"    {i}. t={hit['time']:.1f}s, start={hit['wattage']:.0f}W, "
                      f"avg={hit['avg_wattage']:.0f}W, duration={hit['duration']:.1f}s")
                print(f"       exit: {hit['exit_reason']} at t={hit['exit_time']:.1f}s")
        
        # Cross-validation
        print(f"\n{'─'*80}\nCross-Validation\n{'─'*80}")
        
        if band_entry['status'] == 'ENTERED' and summary['first_sustained_hit_time'] is not None:
            band_time = band_entry['time']
            setpoint_time = summary['first_sustained_hit_time']
            
            print(f"  Band Entry Time:  {band_time:.1f}s")
            print(f"  Setpoint Hit Time: {setpoint_time:.1f}s")
            print(f"  Difference:       {abs(band_time - setpoint_time):.1f}s")
            
            # Band entry should occur before or near setpoint hit
            # (Band is wider tolerance, so should enter first)
            if band_time <= setpoint_time + 5:  # Allow 5s margin
                print(f"  ✅ Band entry occurs at or before setpoint (expected)")
            else:
                print(f"  ⚠️  Band entry after setpoint (unexpected)")
        
        print(f"\n✅ All time metrics calculated successfully for {filepath.name}\n")
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




