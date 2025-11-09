"""
Integration tests for the full metric calculation pipeline.

Tests the complete workflow from CSV file input through all metric calculations
to final results output, including error handling and performance validation.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from src.metrics.orchestrator import MetricOrchestrator


@pytest.mark.integration
class TestOrchestratorIntegration:
    """Integration tests for MetricOrchestrator with full pipeline"""
    
    def test_full_pipeline_upstep_success(self, temp_upstep_csv):
        """Test complete pipeline with UP-STEP CSV file"""
        orchestrator = MetricOrchestrator()
        result = orchestrator.process_file(temp_upstep_csv)
        
        # Validate success
        assert result['success'] is True
        assert 'metrics' in result
        assert 'metadata' in result
        assert 'raw_data' in result
        
        # Validate all 10 metrics present
        expected_metrics = [
            'start_power', 'target_power', 'step_direction',
            'temperature_ranges', 'band_entry', 'setpoint_hit',
            'stable_plateau', 'sharp_drops', 'spikes',
            'overshoot_undershoot'
        ]
        for metric in expected_metrics:
            assert metric in result['metrics'], f"Missing metric: {metric}"
        
        # Validate processing time
        assert 'processing_time_seconds' in result['metadata']
        assert result['metadata']['processing_time_seconds'] < 1.0, "Processing too slow"
        
        # Validate step direction is UP-STEP
        assert result['metrics']['step_direction']['direction'] == 'UP-STEP'
        
        # Validate validation occurred
        assert 'validation' in result['metadata']
        assert 'valid' in result['metadata']['validation']
        assert 'warnings' in result['metadata']['validation']
        assert 'errors' in result['metadata']['validation']
    
    def test_full_pipeline_downstep_success(self, temp_downstep_csv):
        """Test complete pipeline with DOWN-STEP CSV file"""
        orchestrator = MetricOrchestrator()
        result = orchestrator.process_file(temp_downstep_csv)
        
        assert result['success'] is True
        assert result['metrics']['step_direction']['direction'] == 'DOWN-STEP'
        
        # Verify undershoot field exists (DOWN-STEP specific)
        overshoot_undershoot = result['metrics']['overshoot_undershoot']
        assert 'undershoot' in overshoot_undershoot
        assert 'occurred' in overshoot_undershoot['undershoot']
    
    def test_full_pipeline_with_drops(self, temp_with_drops_csv):
        """Test pipeline with CSV containing power drops"""
        orchestrator = MetricOrchestrator()
        result = orchestrator.process_file(temp_with_drops_csv)
        
        assert result['success'] is True
        
        # Sharp drops should be detected
        sharp_drops = result['metrics']['sharp_drops']
        assert 'summary' in sharp_drops
        assert 'count' in sharp_drops['summary']
        assert sharp_drops['summary']['count'] > 0, "Expected to detect power drops"
    
    def test_orchestrator_get_summary(self, temp_upstep_csv):
        """Test get_summary method after processing"""
        orchestrator = MetricOrchestrator()
        result = orchestrator.process_file(temp_upstep_csv)
        
        assert result['success'] is True
        
        # Get summary
        summary = orchestrator.get_summary()
        
        # Validate summary structure
        assert 'file' in summary
        assert 'processing_time' in summary
        assert 'test_type' in summary
        assert 'power_transition' in summary
        assert 'timing' in summary
        assert 'anomalies' in summary
        assert 'temperature' in summary
        
        # Validate power_transition contents
        power = summary['power_transition']
        assert 'start' in power
        assert 'target_before' in power
        assert 'target_after' in power
        assert 'delta' in power
        
        # Validate timing contents
        timing = summary['timing']
        assert 'band_entry' in timing
        assert 'setpoint_hit' in timing
        assert 'stable_plateaus' in timing
        
        # Validate anomalies contents
        anomalies = summary['anomalies']
        assert 'sharp_drops' in anomalies
        assert 'spikes' in anomalies
        assert 'overshoot' in anomalies
        assert 'undershoot' in anomalies
    
    def test_error_handling_missing_file(self):
        """Test error handling for non-existent file"""
        orchestrator = MetricOrchestrator()
        result = orchestrator.process_file('nonexistent_file.csv')
        
        # Should return error result
        assert result['success'] is False
        assert 'error' in result
        assert 'error_type' in result
        assert 'metadata' in result
        assert result['error_type'] == 'FileFormatError'
    
    def test_validation_warnings(self, sample_upstep_df, tmp_path):
        """Test that validation warnings are captured"""
        # Create CSV with slightly different start and target power
        df = sample_upstep_df.copy()
        
        # Modify to create discrepancy
        df.loc[df['miner.seconds'] < 0, 'miner.summary.wattage'] = 1900.0
        df.loc[df['miner.seconds'] < 0, 'miner.mode.power'] = 2000.0
        df.loc[df['miner.seconds'] >= 0, 'miner.mode.power'] = 3000.0
        
        csv_path = tmp_path / "test_warnings.csv"
        df.to_csv(csv_path, index=False)
        
        orchestrator = MetricOrchestrator()
        result = orchestrator.process_file(str(csv_path))
        
        assert result['success'] is True
        
        # Check if validation ran
        validation = result['metadata']['validation']
        assert 'warnings' in validation
        # Warnings may or may not be present depending on data
    
    def test_result_structure_completeness(self, temp_upstep_csv):
        """Test that result contains all expected top-level keys"""
        orchestrator = MetricOrchestrator()
        result = orchestrator.process_file(temp_upstep_csv)
        
        assert result['success'] is True
        
        # Top-level keys
        required_keys = {'success', 'metrics', 'metadata', 'raw_data'}
        assert required_keys.issubset(result.keys())
        
        # Metadata keys
        required_metadata = {
            'filename', 'total_rows', 'action_index', 'action_time',
            'processing_time_seconds', 'validation'
        }
        assert required_metadata.issubset(result['metadata'].keys())
    
    def test_raw_data_format(self, temp_upstep_csv):
        """Test that raw_data is properly formatted"""
        orchestrator = MetricOrchestrator()
        result = orchestrator.process_file(temp_upstep_csv)
        
        assert result['success'] is True
        assert 'raw_data' in result
        assert isinstance(result['raw_data'], list)
        assert len(result['raw_data']) > 0
        
        # Check first row structure
        first_row = result['raw_data'][0]
        assert isinstance(first_row, dict)
        
        # Should have standardized column names
        expected_cols = {'seconds', 'mode_power', 'summary_wattage', 
                        'temp_hash_board_max', 'psu_temp_max', 'outage'}
        assert expected_cols.issubset(first_row.keys())
    
    def test_multiple_files_same_orchestrator(self, temp_upstep_csv, temp_downstep_csv):
        """Test processing multiple files with same orchestrator instance"""
        orchestrator = MetricOrchestrator()
        
        # Process first file
        result1 = orchestrator.process_file(temp_upstep_csv)
        assert result1['success'] is True
        assert result1['metrics']['step_direction']['direction'] == 'UP-STEP'
        
        # Process second file (orchestrator should reset)
        result2 = orchestrator.process_file(temp_downstep_csv)
        assert result2['success'] is True
        assert result2['metrics']['step_direction']['direction'] == 'DOWN-STEP'
        
        # Results should be independent
        assert result1['metrics']['step_direction']['delta'] != result2['metrics']['step_direction']['delta']


@pytest.mark.integration
class TestOrchestratorWithRealFixtures:
    """Integration tests using real CSV fixture files"""
    
    def test_with_real_upstep_fixture(self, real_upstep_csv):
        """Test with real UP-STEP CSV fixture"""
        if not Path(real_upstep_csv).exists():
            pytest.skip("Real fixture file not available")
        
        orchestrator = MetricOrchestrator()
        result = orchestrator.process_file(real_upstep_csv)
        
        assert result['success'] is True
        assert result['metrics']['step_direction']['direction'] == 'UP-STEP'
        assert result['metadata']['processing_time_seconds'] < 1.0
    
    def test_with_real_downstep_fixture(self, real_downstep_csv):
        """Test with real DOWN-STEP CSV fixture"""
        if not Path(real_downstep_csv).exists():
            pytest.skip("Real fixture file not available")
        
        orchestrator = MetricOrchestrator()
        result = orchestrator.process_file(real_downstep_csv)
        
        assert result['success'] is True
        assert result['metrics']['step_direction']['direction'] == 'DOWN-STEP'
        assert result['metadata']['processing_time_seconds'] < 1.0
    
    def test_with_real_valid_profile(self, real_valid_profile_csv):
        """Test with real valid power profile fixture"""
        if not Path(real_valid_profile_csv).exists():
            pytest.skip("Real fixture file not available")
        
        orchestrator = MetricOrchestrator()
        result = orchestrator.process_file(real_valid_profile_csv)
        
        assert result['success'] is True
        # All metrics should be calculated
        assert len(result['metrics']) == 10


@pytest.mark.integration
@pytest.mark.slow
class TestOrchestratorPerformance:
    """Performance and stress tests for orchestrator"""
    
    def test_processing_time_small_file(self, temp_upstep_csv):
        """Test that small files process quickly"""
        orchestrator = MetricOrchestrator()
        result = orchestrator.process_file(temp_upstep_csv)
        
        assert result['success'] is True
        # Should process in < 0.5 seconds for small files
        assert result['metadata']['processing_time_seconds'] < 0.5
    
    def test_large_file_performance(self, tmp_path):
        """Test processing performance with large dataset"""
        # Create large dataset (3600 seconds = 1 hour at 1Hz)
        from tests.fixtures.sample_data import create_upstep_test_data
        
        large_df = create_upstep_test_data(
            start_power=2000.0,
            target_power=3000.0,
            pre_duration=1800,  # 30 minutes
            post_duration=1800,  # 30 minutes
        )
        
        csv_path = tmp_path / "large_test.csv"
        large_df.to_csv(csv_path, index=False)
        
        orchestrator = MetricOrchestrator()
        result = orchestrator.process_file(str(csv_path))
        
        assert result['success'] is True
        # Should still process reasonably fast (< 2 seconds)
        assert result['metadata']['processing_time_seconds'] < 2.0
        print(f"Large file processing time: {result['metadata']['processing_time_seconds']:.3f}s")
    
    def test_batch_processing_performance(self, real_fixtures_dir):
        """Test processing multiple files in sequence"""
        import time
        
        orchestrator = MetricOrchestrator()
        csv_files = list(Path(real_fixtures_dir).glob('*.csv'))
        
        # Filter to valid test files (exclude invalid_types, missing_columns)
        valid_files = [f for f in csv_files if 'invalid' not in f.name and 'missing' not in f.name]
        
        if len(valid_files) < 2:
            pytest.skip("Not enough real fixture files for batch test")
        
        start_time = time.time()
        results = []
        
        for csv_file in valid_files[:5]:  # Test with first 5 files
            result = orchestrator.process_file(str(csv_file))
            results.append(result)
        
        total_time = time.time() - start_time
        
        # All should succeed
        assert all(r['success'] for r in results)
        
        # Average processing time should be reasonable
        avg_time = total_time / len(results)
        assert avg_time < 0.5, f"Average processing time too high: {avg_time:.3f}s"
        print(f"Batch processing: {len(results)} files in {total_time:.3f}s (avg: {avg_time:.3f}s/file)")


@pytest.mark.integration
class TestOrchestratorEdgeCases:
    """Edge case tests for orchestrator"""
    
    def test_minimal_valid_dataset(self, tmp_path):
        """Test with minimal but valid dataset"""
        # Minimum viable dataset: pre-action and post-action data
        df = pd.DataFrame({
            'miner.seconds': [-10, -5, 0, 5, 10],
            'miner.mode.power': [2000, 2000, 3000, 3000, 3000],
            'miner.summary.wattage': [1990, 2000, 2500, 2950, 3000],
            'miner.temp.hash_board_max': [60, 61, 62, 63, 64],
            'miner.psu.temp_max': [45, 46, 47, 48, 49],
            'miner.outage': [False, False, False, False, False]
        })
        
        csv_path = tmp_path / "minimal.csv"
        df.to_csv(csv_path, index=False)
        
        orchestrator = MetricOrchestrator()
        result = orchestrator.process_file(str(csv_path))
        
        # Should process successfully
        assert result['success'] is True
        assert len(result['metrics']) == 10
    
    def test_all_values_constant(self, tmp_path):
        """Test when all power values are constant"""
        df = pd.DataFrame({
            'miner.seconds': list(range(-100, 100)),
            'miner.mode.power': [3000] * 200,
            'miner.summary.wattage': [3000] * 200,
            'miner.temp.hash_board_max': [65] * 200,
            'miner.psu.temp_max': [50] * 200,
            'miner.outage': [False] * 200
        })
        
        csv_path = tmp_path / "constant.csv"
        df.to_csv(csv_path, index=False)
        
        orchestrator = MetricOrchestrator()
        result = orchestrator.process_file(str(csv_path))
        
        assert result['success'] is True
        # Should detect MINIMAL-STEP (no change)
        assert result['metrics']['step_direction']['direction'] == 'MINIMAL-STEP'
        assert result['metrics']['step_direction']['delta'] == 0.0
    
    def test_ingestion_warnings_captured(self, sample_with_nan_df, tmp_path):
        """Test that ingestion warnings are captured in metadata"""
        csv_path = tmp_path / "with_nans.csv"
        sample_with_nan_df.to_csv(csv_path, index=False)
        
        orchestrator = MetricOrchestrator()
        result = orchestrator.process_file(str(csv_path))
        
        assert result['success'] is True
        assert 'ingestion_warnings' in result['metadata']
        # May or may not have warnings depending on NaN handling

