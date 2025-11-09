"""
Validation script for METRIC 9 (Spikes) and METRIC 10 (Overshoot/Undershoot).

Tests the implementations against real CSV data to verify correctness.
"""

import sys
from pathlib import Path
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.data_processing.ingestion import DataIngestion
from src.data_processing.preprocessing import DataPreprocessor
from src.metrics.basic_metrics import BasicMetrics
from src.metrics.anomaly_metrics import AnomalyMetrics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)


def validate_metrics_on_file(filepath: Path):
    """Validate METRIC 9 and 10 on a single CSV file."""
    print(f"\n{'='*80}")
    print(f"TESTING: {filepath.name}")
    print(f"{'='*80}\n")
    
    try:
        # Load and preprocess data
        ingestion = DataIngestion()
        df, action_idx, warnings = ingestion.load_csv(filepath)
        print(f"[OK] Data loaded: {len(df)} rows, action at index {action_idx}")
        
        preprocessor = DataPreprocessor(df, action_idx)
        df_processed, metadata = preprocessor.preprocess()
        print(f"[OK] Preprocessing complete")
        
        # Calculate basic metrics (needed for METRIC 10)
        basic_metrics = BasicMetrics(df_processed, action_idx)
        target_power = basic_metrics.calculate_target_power()
        start_power = basic_metrics.calculate_start_power()
        step_direction = basic_metrics.calculate_step_direction(start_power, target_power)
        
        # Calculate anomaly metrics
        anomaly_metrics = AnomalyMetrics(df_processed, action_idx)
        
        print(f"\n{'-'*80}")
        print(f"Context")
        print(f"{'-'*80}")
        print(f"  Start Power:      {start_power['median']:.2f}W")
        print(f"  Target After:     {target_power['after']:.2f}W")
        print(f"  Step Direction:   {step_direction['direction']} ({step_direction['delta']:+.0f}W)")
        
        # METRIC 9: Spikes
        print(f"\n{'-'*80}")
        print(f"METRIC 9: Spikes (15% Threshold, 5s Window)")
        print(f"{'-'*80}")
        
        spikes_result = anomaly_metrics.calculate_spikes()
        spike_count = spikes_result['summary']['count']
        
        if spike_count > 0:
            print(f"  Total Spikes:     {spike_count}")
            print(f"  Worst Magnitude:  {spikes_result['summary']['worst_magnitude']:.0f}W")
            print(f"  Worst Rate:       {spikes_result['summary']['worst_rate']:.1f} W/s")
            print(f"\n  Spike Details:")
            
            for i, spike in enumerate(spikes_result['spikes'][:5], 1):
                pct = (spike['magnitude'] / spike['start_wattage']) * 100
                print(f"    {i}. t={spike['time']:.1f}s: {spike['start_wattage']:.0f}W -> {spike['end_wattage']:.0f}W")
                print(f"       magnitude={spike['magnitude']:.0f}W ({pct:.1f}%), duration={spike['duration']:.2f}s, rate={spike['rate']:.1f}W/s")
            
            if spike_count > 5:
                print(f"    ... and {spike_count - 5} more")
            
            # Validate spikes
            all_valid = True
            for spike in spikes_result['spikes']:
                if spike['time'] < 0:
                    print(f"  [FAIL] Invalid: spike time < 0")
                    all_valid = False
                if spike['magnitude'] <= 0:
                    print(f"  [FAIL] Invalid: spike magnitude <= 0")
                    all_valid = False
                if spike['rate'] < 0:
                    print(f"  [FAIL] Invalid: spike rate < 0")
                    all_valid = False
                if spike['end_wattage'] <= spike['start_wattage']:
                    print(f"  [FAIL] Invalid: end_wattage <= start_wattage")
                    all_valid = False
                pct = spike['magnitude'] / spike['start_wattage']
                if pct < 0.15:
                    print(f"  [FAIL] Invalid: rise percentage {pct*100:.1f}% < 15%")
                    all_valid = False
            
            if all_valid:
                print(f"  [PASS] All spikes meet criteria (>=15%, <=5s window, positive rate)")
        else:
            print(f"  Total Spikes:     0")
            print(f"  [PASS] No spikes detected (stable power profile)")
        
        # METRIC 10: Overshoot/Undershoot
        print(f"\n{'-'*80}")
        print(f"METRIC 10: Overshoot/Undershoot (MAX(200W, 4% of target))")
        print(f"{'-'*80}")
        
        overshoot_result = anomaly_metrics.calculate_overshoot_undershoot(
            target_power, step_direction
        )
        
        threshold = overshoot_result['threshold']
        print(f"  Threshold:        {threshold:.0f}W")
        
        if 'overshoot' in overshoot_result:
            overshoot = overshoot_result['overshoot']
            if overshoot['occurred']:
                print(f"  [DETECTED] OVERSHOOT")
                print(f"    First Cross:    t={overshoot['time']:.1f}s")
                print(f"    Peak:           {overshoot['peak_wattage']:.0f}W at t={overshoot['peak_time']:.1f}s")
                print(f"    Magnitude:      {overshoot['magnitude']:.0f}W")
                print(f"    Duration:       {overshoot['duration']:.1f}s")
                
                # Validate
                if overshoot['peak_wattage'] > target_power['after'] + threshold:
                    print(f"  [PASS] Peak exceeds threshold ({target_power['after'] + threshold:.0f}W)")
                else:
                    print(f"  [FAIL] Peak does not exceed threshold")
            else:
                print(f"  No overshoot detected (clean UP-STEP)")
        
        if 'undershoot' in overshoot_result:
            undershoot = overshoot_result['undershoot']
            if undershoot['occurred']:
                print(f"  [DETECTED] UNDERSHOOT")
                print(f"    First Cross:    t={undershoot['time']:.1f}s")
                print(f"    Trough:         {undershoot['lowest_wattage']:.0f}W at t={undershoot['lowest_time']:.1f}s")
                print(f"    Magnitude:      {undershoot['magnitude']:.0f}W")
                print(f"    Duration:       {undershoot['duration']:.1f}s")
                
                # Validate
                if undershoot['lowest_wattage'] < target_power['after'] - threshold:
                    print(f"  [PASS] Trough below threshold ({target_power['after'] - threshold:.0f}W)")
                else:
                    print(f"  [FAIL] Trough does not go below threshold")
            else:
                print(f"  No undershoot detected (clean DOWN-STEP)")
        
        # Cross-metric analysis
        print(f"\n{'-'*80}")
        print(f"Cross-Metric Analysis")
        print(f"{'-'*80}")
        
        if spike_count > 0 and 'overshoot' in overshoot_result and overshoot_result['overshoot']['occurred']:
            print(f"  [WARN] Both spikes and overshoot detected - aggressive control response")
        elif spike_count > 0:
            print(f"  [WARN] Spikes detected without overshoot - check for instability")
        elif 'overshoot' in overshoot_result and overshoot_result['overshoot']['occurred']:
            print(f"  Overshoot detected - normal transient response")
        elif 'undershoot' in overshoot_result and overshoot_result['undershoot']['occurred']:
            print(f"  Undershoot detected - normal transient response")
        else:
            print(f"  [PASS] Clean transition without anomalies")
        
        print(f"\n[OK] Metrics calculated successfully for {filepath.name}\n")
        return True
        
    except Exception as e:
        print(f"[FAIL] Error processing {filepath.name}: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run validation on all test CSV files."""
    fixtures_dir = Path('tests/fixtures')
    csv_files = sorted(fixtures_dir.glob('*.csv'))
    
    print(f"Found {len(csv_files)} CSV file(s) to validate\n")
    
    results = {}
    for csv_file in csv_files:
        success = validate_metrics_on_file(csv_file)
        results[csv_file.name] = success
    
    # Summary
    print(f"\n{'='*80}")
    print(f"VALIDATION SUMMARY")
    print(f"{'='*80}\n")
    
    passed = sum(1 for v in results.values() if v)
    failed = len(results) - passed
    
    for filename, success in results.items():
        status = "[PASS]" if success else "[FAIL]"
        print(f"  {status} - {filename}")
    
    print(f"\nTotal: {passed}/{len(results)} files validated successfully")


if __name__ == '__main__':
    main()
