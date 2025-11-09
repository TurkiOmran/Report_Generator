"""
Comprehensive validation script for batch processing of real CSV files.

This script processes all CSV files in tests/fixtures/real_data/ and generates
a detailed validation report with metrics, performance stats, and issue tracking.
"""

import os
import glob
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from src.metrics.orchestrator import MetricOrchestrator
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('validation_batch.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ValidationReport:
    """Manages validation results and report generation."""
    
    def __init__(self):
        self.results = []
        self.summary = {
            'total_files': 0,
            'successful': 0,
            'failed': 0,
            'total_processing_time': 0.0,
            'average_processing_time': 0.0,
            'issues_found': [],
            'performance_stats': {},
            'metric_stats': {}
        }
    
    def add_result(self, filename: str, result: Dict[str, Any], processing_time: float):
        """Add a file processing result."""
        self.results.append({
            'filename': filename,
            'success': result.get('success', False),
            'processing_time': processing_time,
            'result': result
        })
        
        self.summary['total_files'] += 1
        if result.get('success'):
            self.summary['successful'] += 1
        else:
            self.summary['failed'] += 1
            self.summary['issues_found'].append({
                'file': filename,
                'error': result.get('error', 'Unknown error'),
                'error_type': result.get('error_type', 'Unknown')
            })
        
        self.summary['total_processing_time'] += processing_time
    
    def calculate_summary(self):
        """Calculate summary statistics."""
        if self.summary['total_files'] > 0:
            self.summary['average_processing_time'] = (
                self.summary['total_processing_time'] / self.summary['total_files']
            )
        
        # Performance stats
        successful_times = [
            r['processing_time'] for r in self.results if r['success']
        ]
        if successful_times:
            self.summary['performance_stats'] = {
                'min_time': min(successful_times),
                'max_time': max(successful_times),
                'avg_time': sum(successful_times) / len(successful_times)
            }
        
        # Metric stats - collect all metric values from successful runs
        metric_values = {}
        for result in self.results:
            if result['success'] and 'metrics' in result['result']:
                metrics = result['result']['metrics']
                
                # Step direction distribution
                step_dir = metrics.get('step_direction', {}).get('direction', 'unknown')
                if 'step_direction' not in metric_values:
                    metric_values['step_direction'] = {}
                metric_values['step_direction'][step_dir] = (
                    metric_values['step_direction'].get(step_dir, 0) + 1
                )
                
                # Band entry stats
                if 'band_entry' not in metric_values:
                    metric_values['band_entry'] = {'achieved': 0, 'not_achieved': 0}
                if metrics.get('band_entry', {}).get('achieved'):
                    metric_values['band_entry']['achieved'] += 1
                else:
                    metric_values['band_entry']['not_achieved'] += 1
                
                # Anomaly counts
                sharp_drops = metrics.get('sharp_drops', {}).get('summary', {}).get('count', 0)
                sharp_rises = metrics.get('sharp_rises', {}).get('summary', {}).get('count', 0)
                
                if 'anomalies' not in metric_values:
                    metric_values['anomalies'] = {
                        'sharp_drops': [],
                        'sharp_rises': [],
                        'overshoot': 0,
                        'undershoot': 0
                    }
                
                metric_values['anomalies']['sharp_drops'].append(sharp_drops)
                metric_values['anomalies']['sharp_rises'].append(sharp_rises)
                
                if metrics.get('overshoot_undershoot', {}).get('overshoot', {}).get('occurred'):
                    metric_values['anomalies']['overshoot'] += 1
                if metrics.get('overshoot_undershoot', {}).get('undershoot', {}).get('occurred'):
                    metric_values['anomalies']['undershoot'] += 1
        
        self.summary['metric_stats'] = metric_values
    
    def generate_markdown_report(self, output_file: str = 'VALIDATION_REPORT.md'):
        """Generate detailed markdown report."""
        self.calculate_summary()
        
        report = []
        report.append("# Validation Report - Real CSV Data Testing\n")
        report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report.append("---\n\n")
        
        # Summary section
        report.append("## 📊 Summary Statistics\n")
        report.append(f"- **Total Files Processed:** {self.summary['total_files']}")
        report.append(f"- **Successful:** {self.summary['successful']} ✅")
        report.append(f"- **Failed:** {self.summary['failed']} ❌")
        report.append(f"- **Success Rate:** {(self.summary['successful']/self.summary['total_files']*100):.1f}%")
        report.append(f"- **Total Processing Time:** {self.summary['total_processing_time']:.3f}s")
        report.append(f"- **Average Processing Time:** {self.summary['average_processing_time']:.3f}s\n")
        
        # Performance stats
        if self.summary['performance_stats']:
            report.append("## ⚡ Performance Statistics\n")
            perf = self.summary['performance_stats']
            report.append(f"- **Fastest File:** {perf['min_time']:.3f}s")
            report.append(f"- **Slowest File:** {perf['max_time']:.3f}s")
            report.append(f"- **Average Time:** {perf['avg_time']:.3f}s\n")
        
        # Metric statistics
        if self.summary['metric_stats']:
            report.append("## 📈 Metric Statistics\n")
            
            # Step direction distribution
            if 'step_direction' in self.summary['metric_stats']:
                report.append("### Step Direction Distribution:")
                for direction, count in self.summary['metric_stats']['step_direction'].items():
                    report.append(f"- **{direction}:** {count} files")
                report.append("")
            
            # Band entry
            if 'band_entry' in self.summary['metric_stats']:
                be = self.summary['metric_stats']['band_entry']
                total = be['achieved'] + be['not_achieved']
                if total > 0:
                    report.append("### Band Entry Achievement:")
                    report.append(f"- **Achieved:** {be['achieved']} ({be['achieved']/total*100:.1f}%)")
                    report.append(f"- **Not Achieved:** {be['not_achieved']} ({be['not_achieved']/total*100:.1f}%)\n")
            
            # Anomalies
            if 'anomalies' in self.summary['metric_stats']:
                anom = self.summary['metric_stats']['anomalies']
                report.append("### Anomaly Detection:")
                if anom['sharp_drops']:
                    avg_drops = sum(anom['sharp_drops']) / len(anom['sharp_drops'])
                    max_drops = max(anom['sharp_drops'])
                    report.append(f"- **Sharp Drops:** Avg {avg_drops:.1f}, Max {max_drops}")
                if anom['sharp_rises']:
                    avg_rises = sum(anom['sharp_rises']) / len(anom['sharp_rises'])
                    max_rises = max(anom['sharp_rises'])
                    report.append(f"- **Sharp Rises:** Avg {avg_rises:.1f}, Max {max_rises}")
                report.append(f"- **Overshoot Detected:** {anom['overshoot']} files")
                report.append(f"- **Undershoot Detected:** {anom['undershoot']} files\n")
        
        # Issues found
        if self.summary['issues_found']:
            report.append("## ⚠️ Issues Found\n")
            for issue in self.summary['issues_found']:
                report.append(f"### ❌ {issue['file']}")
                report.append(f"- **Error Type:** {issue['error_type']}")
                report.append(f"- **Error Message:** {issue['error']}\n")
        
        # Detailed results per file
        report.append("## 📝 Detailed Results Per File\n")
        for result in self.results:
            filename = result['filename']
            success = result['success']
            proc_time = result['processing_time']
            
            status_icon = "✅" if success else "❌"
            report.append(f"### {status_icon} {filename}")
            report.append(f"- **Processing Time:** {proc_time:.3f}s\n")
            
            if success:
                metrics = result['result'].get('metrics', {})
                metadata = result['result'].get('metadata', {})
                
                # Display ALL metrics in detail
                report.append("#### 📊 Complete Metrics Report\n")
                
                # 1. Start Power
                if 'start_power' in metrics:
                    sp = metrics['start_power']
                    report.append("**METRIC 1: Start Power**")
                    report.append(f"- Median: {sp.get('median', 'N/A')}W")
                    report.append(f"- Last Value: {sp.get('last_value', 'N/A')}W")
                    report.append(f"- Difference: {sp.get('difference', 'N/A')}W")
                    if sp.get('note'):
                        report.append(f"- Note: {sp.get('note')}")
                    report.append("")
                
                # 2. Target Power
                if 'target_power' in metrics:
                    tp = metrics['target_power']
                    report.append("**METRIC 2: Target Power**")
                    report.append(f"- Before: {tp.get('before', 'N/A')}W")
                    report.append(f"- After: {tp.get('after', 'N/A')}W")
                    report.append(f"- Change: {tp.get('change', 'N/A')}W")
                    report.append("")
                
                # 3. Step Direction
                if 'step_direction' in metrics:
                    sd = metrics['step_direction']
                    report.append("**METRIC 3: Step Direction**")
                    report.append(f"- Direction: {sd.get('direction', 'N/A')}")
                    report.append(f"- Delta: {sd.get('delta', 'N/A')}W")
                    report.append(f"- Description: {sd.get('description', 'N/A')}")
                    report.append("")
                
                # 4. Temperature Ranges
                if 'temperature_ranges' in metrics:
                    tr = metrics['temperature_ranges']
                    report.append("**METRIC 4: Temperature Ranges**")
                    board = tr.get('board', {})
                    psu = tr.get('psu', {})
                    report.append(f"- Hash Board: Min={board.get('min', 'N/A')}°C, Max={board.get('max', 'N/A')}°C, Range={board.get('range', 'N/A')}°C")
                    report.append(f"- PSU: Min={psu.get('min', 'N/A')}°C, Max={psu.get('max', 'N/A')}°C, Range={psu.get('range', 'N/A')}°C")
                    report.append("")
                
                # 5. Band Entry
                if 'band_entry' in metrics:
                    be = metrics['band_entry']
                    report.append("**METRIC 5: Band Entry**")
                    report.append(f"- Status: {be.get('status', 'N/A')}")
                    report.append(f"- Time: {be.get('time', 'N/A')}s")
                    report.append(f"- Wattage: {be.get('wattage', 'N/A')}W")
                    report.append(f"- Percentage: {be.get('percentage', 'N/A')}%")
                    if 'band_limits' in be:
                        limits = be['band_limits']
                        report.append(f"- Band Limits: {limits.get('lower', 'N/A')}W - {limits.get('upper', 'N/A')}W (±{limits.get('tolerance', 'N/A')}W)")
                    report.append(f"- Entry Method: {be.get('entry_method', 'N/A')}")
                    report.append("")
                
                # 6. Setpoint Hit
                if 'setpoint_hit' in metrics:
                    sh = metrics['setpoint_hit']
                    report.append("**METRIC 6: Setpoint Hit**")
                    sustained = sh.get('sustained_hits', [])
                    brief = sh.get('brief_touches', [])
                    report.append(f"- Sustained Hits: {len(sustained)}")
                    report.append(f"- Brief Touches: {len(brief)}")
                    if brief:
                        times = [f"t={b.get('time', 'N/A')}s" for b in brief]
                        report.append(f"- Brief Touch Times: {', '.join(times)}")
                    if sustained:
                        first_hit = sustained[0]
                        report.append(f"- First Sustained Hit: Time={first_hit.get('time', 'N/A')}s, Duration={first_hit.get('duration', 'N/A')}s")
                    report.append("")
                
                # 7. Stable Plateau
                if 'stable_plateau' in metrics:
                    spl = metrics['stable_plateau']
                    summary = spl.get('summary', {})
                    plateaus = spl.get('plateaus', [])
                    report.append("**METRIC 7: Stable Plateau**")
                    report.append(f"- Total Plateaus: {summary.get('total_count', 0)}")
                    report.append(f"- Longest Duration: {summary.get('longest_duration', 0.0)}s")
                    report.append(f"- Total Stable Time: {summary.get('total_stable_time', 0.0)}s")
                    if plateaus:
                        plateau_ranges = []
                        for p in plateaus:
                            start = p.get('start_time', 'N/A')
                            end = p.get('exit_time', 'N/A')
                            plateau_ranges.append(f"t={start:.1f}-{end:.1f}s")
                        report.append(f"- Plateau Ranges: {' and '.join(plateau_ranges)}")
                    report.append("")
                
                # 8. Sharp Drops
                if 'sharp_drops' in metrics:
                    drops = metrics['sharp_drops']
                    summary = drops.get('summary', {})
                    drop_list = drops.get('sharp_drops', [])
                    report.append("**METRIC 8: Sharp Drops**")
                    report.append(f"- Count: {summary.get('count', 0)}")
                    report.append(f"- Threshold: N/A%")
                    if drop_list:
                        times = [f"t={d.get('time', 'N/A')}s" for d in drop_list]
                        report.append(f"- Times: {', '.join(times)}")
                    report.append("")
                
                # 9. Sharp Rises
                if 'sharp_rises' in metrics:
                    sharp_rises = metrics['sharp_rises']
                    summary = sharp_rises.get('summary', {})
                    rise_list = sharp_rises.get('sharp_rises', [])
                    report.append("**METRIC 9: Sharp Rises**")
                    report.append(f"- Count: {summary.get('count', 0)}")
                    report.append(f"- Threshold: N/A%")
                    if rise_list:
                        times = [f"t={r.get('time', 'N/A')}s" for r in rise_list]
                        report.append(f"- Times: {', '.join(times)}")
                    report.append("")
                
                # 10. Overshoot/Undershoot
                if 'overshoot_undershoot' in metrics:
                    ou = metrics['overshoot_undershoot']
                    overshoot = ou.get('overshoot')
                    undershoot = ou.get('undershoot')
                    report.append("**METRIC 10: Overshoot/Undershoot**")
                    
                    # Only show overshoot if present (ramping up)
                    if overshoot is not None:
                        report.append(f"- Overshoot Occurred: {overshoot.get('occurred', False)}")
                        if overshoot.get('occurred'):
                            report.append(f"  - Peak Power: {overshoot.get('peak_wattage', 'N/A')}W")
                            report.append(f"  - Peak Time: {overshoot.get('peak_time', 'N/A')}s")
                            report.append(f"  - Magnitude: {overshoot.get('magnitude', 'N/A')}W")
                            report.append(f"  - Duration: {overshoot.get('duration', 'N/A')}s")
                    
                    # Only show undershoot if present (ramping down)
                    if undershoot is not None:
                        report.append(f"- Undershoot Occurred: {undershoot.get('occurred', False)}")
                        if undershoot.get('occurred'):
                            report.append(f"  - Lowest Power: {undershoot.get('lowest_wattage', 'N/A')}W")
                            report.append(f"  - Lowest Time: {undershoot.get('lowest_time', 'N/A')}s")
                            report.append(f"  - Magnitude: {undershoot.get('magnitude', 'N/A')}W")
                            report.append(f"  - Duration: {undershoot.get('duration', 'N/A')}s")
                    report.append("")
                
                # Metadata section
                report.append("#### 📋 Metadata\n")
                report.append(f"- Total Rows: {metadata.get('total_rows', 'N/A')}")
                report.append(f"- Action Index: {metadata.get('action_index', 'N/A')}")
                report.append(f"- Action Time: {metadata.get('action_time', 'N/A')}s")
                
                validation = metadata.get('validation', {})
                if validation:
                    report.append(f"- Valid Metrics: {validation.get('valid_count', 0)}/{validation.get('total_count', 0)}")
                    if validation.get('warnings'):
                        report.append(f"- Warnings: {len(validation['warnings'])}")
                        for warning in validation['warnings'][:3]:  # Show first 3 warnings
                            report.append(f"  - {warning}")
                    if validation.get('errors'):
                        report.append(f"- Errors: {len(validation['errors'])}")
                        for error in validation['errors'][:3]:  # Show first 3 errors
                            report.append(f"  - {error}")
                report.append("")
                
            else:
                report.append(f"**Error:** {result['result'].get('error', 'Unknown')}\n")
            
            report.append("---\n")
        
        # Write report
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        logger.info(f"Report generated: {output_file}")
        return output_file


def validate_real_data_batch():
    """
    Main validation function - processes all CSV files in real_data directory.
    """
    logger.info("="*80)
    logger.info(" REAL DATA BATCH VALIDATION")
    logger.info("="*80)
    
    # Find all CSV files
    data_dir = Path(__file__).parent / "tests" / "fixtures" / "real_data"
    csv_files = list(data_dir.glob("*.csv"))
    
    if not csv_files:
        logger.warning(f"No CSV files found in {data_dir}")
        logger.info("Please place your CSV files in tests/fixtures/real_data/")
        return
    
    logger.info(f"Found {len(csv_files)} CSV files to process\n")
    
    # Initialize report
    report = ValidationReport()
    orchestrator = MetricOrchestrator()
    
    # Process each file
    for i, csv_file in enumerate(csv_files, 1):
        filename = csv_file.name
        logger.info(f"[{i}/{len(csv_files)}] Processing: {filename}")
        
        start_time = time.time()
        try:
            result = orchestrator.process_file(str(csv_file))
            processing_time = time.time() - start_time
            
            if result['success']:
                logger.info(f"  ✅ Success ({processing_time:.3f}s)")
            else:
                logger.error(f"  ❌ Failed: {result.get('error', 'Unknown error')}")
            
            report.add_result(filename, result, processing_time)
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"  ❌ Exception: {str(e)}")
            report.add_result(filename, {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }, processing_time)
        
        logger.info("")
    
    # Generate report
    logger.info("="*80)
    logger.info(" GENERATING REPORT")
    logger.info("="*80)
    
    report_file = report.generate_markdown_report()
    
    # Print summary
    logger.info("\n" + "="*80)
    logger.info(" VALIDATION SUMMARY")
    logger.info("="*80)
    logger.info(f"Total Files:     {report.summary['total_files']}")
    logger.info(f"Successful:      {report.summary['successful']} ✅")
    logger.info(f"Failed:          {report.summary['failed']} ❌")
    logger.info(f"Success Rate:    {(report.summary['successful']/report.summary['total_files']*100):.1f}%")
    logger.info(f"Total Time:      {report.summary['total_processing_time']:.3f}s")
    logger.info(f"Average Time:    {report.summary['average_processing_time']:.3f}s")
    logger.info(f"\nReport saved to: {report_file}")
    logger.info("="*80)
    
    return report


if __name__ == "__main__":
    validate_real_data_batch()

