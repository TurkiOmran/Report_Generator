"""
Validation script for the Metric Orchestrator.

Tests the full pipeline from CSV ingestion through all metric calculations.
"""

import sys
import json
from pathlib import Path
from src.metrics.orchestrator import MetricOrchestrator


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def validate_orchestrator():
    """Run orchestrator validation against test fixtures."""
    
    # Get test fixtures
    fixtures_dir = Path("tests/fixtures")
    if not fixtures_dir.exists():
        print(f"[FAIL] Fixtures directory not found: {fixtures_dir}")
        return False
    
    csv_files = list(fixtures_dir.glob("*.csv"))
    if not csv_files:
        print(f"[FAIL] No CSV files found in {fixtures_dir}")
        return False
    
    print_section("METRIC ORCHESTRATOR VALIDATION")
    print(f"Found {len(csv_files)} test fixture(s)")
    
    # Test each fixture
    all_passed = True
    orchestrator = MetricOrchestrator()
    
    for csv_file in csv_files:
        print_section(f"Processing: {csv_file.name}")
        
        try:
            # Process file
            result = orchestrator.process_file(str(csv_file))
            
            # Check success
            if not result.get('success'):
                print(f"[FAIL] Processing failed")
                print(f"  Error: {result.get('error')}")
                print(f"  Type: {result.get('error_type')}")
                all_passed = False
                continue
            
            print("[OK] Processing succeeded")
            
            # Check all metrics present
            metrics = result.get('metrics', {})
            expected_metrics = [
                'start_power', 'target_power', 'step_direction',
                'temperature_ranges', 'band_entry', 'setpoint_hit',
                'stable_plateau', 'sharp_drops', 'spikes',
                'overshoot_undershoot'
            ]
            
            missing_metrics = [m for m in expected_metrics if m not in metrics]
            if missing_metrics:
                print(f"[FAIL] Missing metrics: {', '.join(missing_metrics)}")
                all_passed = False
            else:
                print(f"[OK] All {len(expected_metrics)} metrics calculated")
            
            # Check metadata
            metadata = result.get('metadata', {})
            if 'processing_time_seconds' not in metadata:
                print("[FAIL] Missing processing_time_seconds in metadata")
                all_passed = False
            else:
                proc_time = metadata['processing_time_seconds']
                print(f"[OK] Processing time: {proc_time}s")
                
                if proc_time > 2.0:
                    print(f"[WARN] Processing took longer than expected ({proc_time}s > 2.0s)")
            
            # Check validation
            validation = metadata.get('validation', {})
            if not validation.get('valid'):
                print("[WARN] Validation found issues:")
                for error in validation.get('errors', []):
                    print(f"  - ERROR: {error}")
                for warning in validation.get('warnings', []):
                    print(f"  - WARN: {warning}")
            else:
                print("[OK] Validation passed")
                warnings = validation.get('warnings', [])
                if warnings:
                    print(f"[OK] {len(warnings)} warning(s) noted:")
                    for warning in warnings:
                        print(f"  - {warning}")
            
            # Display summary
            print("\n--- Metric Summary ---")
            summary = orchestrator.get_summary()
            
            # Power transition
            power = summary.get('power_transition', {})
            print(f"Power Transition:")
            print(f"  Start: {power.get('start'):.0f}W")
            print(f"  Target Before: {power.get('target_before'):.0f}W")
            print(f"  Target After: {power.get('target_after'):.0f}W")
            print(f"  Delta: {power.get('delta'):.0f}W")
            print(f"  Test Type: {summary.get('test_type')}")
            
            # Timing metrics
            timing = summary.get('timing', {})
            print(f"\nTiming:")
            band_entry = timing.get('band_entry')
            setpoint_hit = timing.get('setpoint_hit')
            print(f"  Band Entry: {band_entry:.2f}s" if band_entry else "  Band Entry: Not achieved")
            print(f"  Setpoint Hit: {setpoint_hit:.2f}s" if setpoint_hit else "  Setpoint Hit: Not achieved")
            print(f"  Stable Plateaus: {timing.get('stable_plateaus')}")
            
            # Anomalies
            anomalies = summary.get('anomalies', {})
            print(f"\nAnomalies:")
            print(f"  Sharp Drops: {anomalies.get('sharp_drops')}")
            print(f"  Spikes: {anomalies.get('spikes')}")
            print(f"  Overshoot: {'Yes' if anomalies.get('overshoot') else 'No'}")
            print(f"  Undershoot: {'Yes' if anomalies.get('undershoot') else 'No'}")
            
            # Temperature
            temp = summary.get('temperature', {})
            print(f"\nTemperature:")
            hb_max = temp.get('hash_board_max')
            psu_max = temp.get('psu_max')
            print(f"  Hash Board Max: {hb_max:.1f}C" if hb_max else "  Hash Board Max: N/A")
            print(f"  PSU Max: {psu_max:.1f}C" if psu_max else "  PSU Max: N/A")
            
        except Exception as e:
            print(f"[FAIL] Exception during processing: {e}")
            import traceback
            traceback.print_exc()
            all_passed = False
    
    # Final summary
    print_section("VALIDATION COMPLETE")
    if all_passed:
        print("[OK] All tests passed!")
        return True
    else:
        print("[FAIL] Some tests failed")
        return False


if __name__ == "__main__":
    success = validate_orchestrator()
    sys.exit(0 if success else 1)

