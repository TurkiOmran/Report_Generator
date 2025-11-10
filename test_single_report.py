"""
Quick Test Script for Single File Report Generation

This script tests the pipeline with a single CSV file and generates
an HTML report.
"""

from src.pipeline import ReportPipeline
import os

def main():
    print("=" * 60)
    print("Testing Single File Report Generation")
    print("=" * 60)
    
    # Configure pipeline
    print("\n1. Initializing pipeline...")
    pipeline = ReportPipeline(
        output_dir='test_reports',
        enable_analysis=False,  # Set to True to enable Claude AI analysis (uses API tokens)
        log_level='INFO'
    )
    print("[OK] Pipeline initialized")
    
    # Test CSV file
    csv_file = 'tests/fixtures/r2_39_2025-08-28T09_40_10.csv'
    
    if not os.path.exists(csv_file):
        print(f"\n[ERROR] Test file not found: {csv_file}")
        return
    
    print(f"\n2. Processing CSV file: {csv_file}")
    print("   This will:")
    print("   - Validate the CSV file")
    print("   - Calculate all metrics")
    print("   - Generate power timeline visualization")
    print("   - Assemble HTML report")
    print("   - Save report to disk")
    
    # Generate report
    result = pipeline.generate_report(csv_file)
    
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    
    if result['success']:
        print(f"\n[SUCCESS] Report generated successfully")
        print(f"\nReport Details:")
        print(f"  - Report path: {result['report_path']}")
        print(f"  - Processing time: {result['duration_seconds']:.2f} seconds")
        print(f"  - AI analysis included: {result['analysis_included']}")
        print(f"  - Metrics calculated: {len(result['metrics'])} metrics")
        
        print(f"\nMetrics Summary:")
        metrics = result['metrics']
        if 'start_power' in metrics:
            print(f"  - Start power: {metrics['start_power'].get('median', 'N/A')} W")
        if 'target_power' in metrics:
            print(f"  - Target power: {metrics['target_power'].get('before', 'N/A')} W -> {metrics['target_power'].get('after', 'N/A')} W")
        if 'step_direction' in metrics:
            print(f"  - Step direction: {metrics['step_direction'].get('direction', 'N/A')}")
        
        print(f"\nMetadata:")
        metadata = result['metadata']
        print(f"  - Total samples: {metadata.get('total_rows', 'N/A')}")
        print(f"  - File: {metadata.get('filename', 'N/A')}")
        
        print(f"\nOpen the report in your browser:")
        print(f"   {os.path.abspath(result['report_path'])}")
        
    else:
        print(f"\n[FAILED] Report generation failed")
        print(f"\nError: {result['error']}")
    
    # Show pipeline statistics
    print(f"\n" + "=" * 60)
    print("Pipeline Statistics")
    print("=" * 60)
    stats = pipeline.get_stats()
    print(f"  Total processed: {stats['total_processed']}")
    print(f"  Successful: {stats['successful']}")
    print(f"  Failed: {stats['failed']}")
    print(f"  Success rate: {stats['success_rate']*100:.1f}%")
    
    print("\n" + "=" * 60)

if __name__ == '__main__':
    main()

