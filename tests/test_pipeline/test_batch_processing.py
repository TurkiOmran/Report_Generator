"""
Tests for Batch Processing

Tests the batch processing functionality for handling multiple CSV files.
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path

from src.pipeline.report_pipeline import (
    ReportPipeline,
    ValidationError
)


class TestBatchProcessing:
    """Test suite for batch processing functionality."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test outputs."""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)
    
    @pytest.fixture
    def batch_csv_dir(self):
        """Path to directory with multiple CSV files."""
        return 'tests/fixtures'
    
    def test_generate_batch_success(self, temp_dir, batch_csv_dir):
        """Test batch processing with multiple valid CSV files."""
        pipeline = ReportPipeline(output_dir=temp_dir, enable_analysis=False)
        
        result = pipeline.generate_batch(batch_csv_dir, pattern='r*_39*.csv')
        
        # Verify batch completed
        assert result['total_files'] > 0
        assert result['successful'] > 0
        assert result['duration_seconds'] > 0
        
        # Verify reports were generated
        assert len(result['reports']) == result['successful']
        for report_path in result['reports']:
            assert os.path.exists(report_path)
    
    def test_generate_batch_empty_directory(self, temp_dir):
        """Test batch processing with empty directory."""
        empty_dir = os.path.join(temp_dir, 'empty')
        os.makedirs(empty_dir)
        
        pipeline = ReportPipeline(output_dir=temp_dir)
        result = pipeline.generate_batch(empty_dir)
        
        assert result['total_files'] == 0
        assert result['successful'] == 0
        assert result['failed'] == 0
        assert result['reports'] == []
    
    def test_generate_batch_nonexistent_directory(self, temp_dir):
        """Test batch processing with nonexistent directory."""
        pipeline = ReportPipeline(output_dir=temp_dir)
        
        with pytest.raises(ValidationError, match="not found"):
            pipeline.generate_batch('/nonexistent/directory')
    
    def test_generate_batch_file_instead_of_directory(self, temp_dir, batch_csv_dir):
        """Test batch processing with file path instead of directory."""
        csv_file = os.path.join(batch_csv_dir, 'r2_39_2025-08-28T09_40_10.csv')
        pipeline = ReportPipeline(output_dir=temp_dir)
        
        with pytest.raises(ValidationError, match="not a directory"):
            pipeline.generate_batch(csv_file)
    
    def test_generate_batch_custom_pattern(self, temp_dir, batch_csv_dir):
        """Test batch processing with custom file pattern."""
        pipeline = ReportPipeline(output_dir=temp_dir, enable_analysis=False)
        
        # Process only files starting with 'r2'
        result = pipeline.generate_batch(batch_csv_dir, pattern='r2*.csv')
        
        assert result['total_files'] > 0
        assert result['successful'] >= 0
    
    def test_generate_batch_with_mixed_files(self, temp_dir):
        """Test batch processing with valid and invalid CSV files."""
        # Create test directory with mixed files
        test_dir = os.path.join(temp_dir, 'mixed')
        os.makedirs(test_dir)
        
        # Copy a valid CSV
        valid_csv = 'tests/fixtures/r2_39_2025-08-28T09_40_10.csv'
        shutil.copy(valid_csv, os.path.join(test_dir, 'valid.csv'))
        
        # Create an invalid CSV
        invalid_csv = os.path.join(test_dir, 'invalid.csv')
        with open(invalid_csv, 'w') as f:
            f.write('garbage,data\n1,2,3')
        
        pipeline = ReportPipeline(output_dir=temp_dir, enable_analysis=False)
        result = pipeline.generate_batch(test_dir)
        
        # Should process all files
        assert result['total_files'] == 2
        # At least one should succeed
        assert result['successful'] >= 1
        # Should track errors
        if result['failed'] > 0:
            assert len(result['errors']) == result['failed']
    
    def test_generate_batch_continue_on_error(self, temp_dir):
        """Test that batch processing continues after errors."""
        # Create test directory with mixed files
        test_dir = os.path.join(temp_dir, 'continue_test')
        os.makedirs(test_dir)
        
        # Create first invalid file
        with open(os.path.join(test_dir, 'a_invalid.csv'), 'w') as f:
            f.write('bad,data')
        
        # Copy valid file
        valid_csv = 'tests/fixtures/r2_39_2025-08-28T09_40_10.csv'
        shutil.copy(valid_csv, os.path.join(test_dir, 'b_valid.csv'))
        
        # Create second invalid file
        with open(os.path.join(test_dir, 'c_invalid.csv'), 'w') as f:
            f.write('more,bad,data')
        
        pipeline = ReportPipeline(output_dir=temp_dir, enable_analysis=False)
        result = pipeline.generate_batch(test_dir, continue_on_error=True)
        
        # Should process all 3 files
        assert result['total_files'] == 3
        # Should have 1 success and 2 failures
        assert result['successful'] == 1
        assert result['failed'] == 2
        assert len(result['errors']) == 2
    
    def test_generate_batch_stop_on_error(self, temp_dir):
        """Test that batch processing stops on first error when configured."""
        # Create test directory
        test_dir = os.path.join(temp_dir, 'stop_test')
        os.makedirs(test_dir)
        
        # Create first invalid file (alphabetically first)
        with open(os.path.join(test_dir, 'a_invalid.csv'), 'w') as f:
            f.write('bad,data')
        
        # Copy valid file
        valid_csv = 'tests/fixtures/r2_39_2025-08-28T09_40_10.csv'
        shutil.copy(valid_csv, os.path.join(test_dir, 'b_valid.csv'))
        
        pipeline = ReportPipeline(output_dir=temp_dir, enable_analysis=False)
        result = pipeline.generate_batch(test_dir, continue_on_error=False)
        
        # Should stop after first file
        assert result['failed'] == 1
        # Should not process remaining files
        assert result['successful'] + result['failed'] < result['total_files']
    
    def test_generate_batch_custom_output_dir(self, temp_dir, batch_csv_dir):
        """Test batch processing with custom output directory."""
        custom_output = os.path.join(temp_dir, 'custom_reports')
        
        pipeline = ReportPipeline(output_dir=temp_dir, enable_analysis=False)
        result = pipeline.generate_batch(
            batch_csv_dir,
            output_dir=custom_output,
            pattern='r2*.csv'
        )
        
        if result['successful'] > 0:
            # Verify reports were saved to custom directory
            assert os.path.exists(custom_output)
            for report_path in result['reports']:
                assert custom_output in report_path
    
    def test_generate_batch_updates_pipeline_stats(self, temp_dir, batch_csv_dir):
        """Test that batch processing updates pipeline statistics."""
        pipeline = ReportPipeline(output_dir=temp_dir, enable_analysis=False)
        
        initial_stats = pipeline.get_stats()
        initial_total = initial_stats['total_processed']
        
        result = pipeline.generate_batch(batch_csv_dir, pattern='r2*.csv')
        
        final_stats = pipeline.get_stats()
        
        # Stats should reflect batch processing
        assert final_stats['total_processed'] == initial_total + result['total_files']
        assert final_stats['successful'] >= initial_stats['successful']
    
    def test_generate_batch_reports_list(self, temp_dir, batch_csv_dir):
        """Test that batch returns list of generated report paths."""
        pipeline = ReportPipeline(output_dir=temp_dir, enable_analysis=False)
        
        result = pipeline.generate_batch(batch_csv_dir, pattern='r2*.csv')
        
        assert 'reports' in result
        assert isinstance(result['reports'], list)
        assert len(result['reports']) == result['successful']
    
    def test_generate_batch_error_details(self, temp_dir):
        """Test that batch provides detailed error information."""
        # Create test directory with invalid file
        test_dir = os.path.join(temp_dir, 'error_test')
        os.makedirs(test_dir)
        
        # Create invalid CSV
        with open(os.path.join(test_dir, 'invalid.csv'), 'w') as f:
            f.write('not,a,valid,power,profile')
        
        pipeline = ReportPipeline(output_dir=temp_dir, enable_analysis=False)
        result = pipeline.generate_batch(test_dir)
        
        if result['failed'] > 0:
            # Should have error details
            assert len(result['errors']) > 0
            error = result['errors'][0]
            assert 'file' in error
            assert 'error' in error
            assert isinstance(error['error'], str)
    
    def test_generate_batch_duration_tracking(self, temp_dir, batch_csv_dir):
        """Test that batch processing tracks duration."""
        pipeline = ReportPipeline(output_dir=temp_dir, enable_analysis=False)
        
        result = pipeline.generate_batch(batch_csv_dir, pattern='r2*.csv')
        
        assert 'duration_seconds' in result
        assert result['duration_seconds'] > 0
        assert isinstance(result['duration_seconds'], (int, float))
    
    def test_generate_batch_logging(self, temp_dir, batch_csv_dir, caplog):
        """Test that batch processing produces appropriate logs."""
        pipeline = ReportPipeline(output_dir=temp_dir, enable_analysis=False)
        
        result = pipeline.generate_batch(batch_csv_dir, pattern='r2*.csv')
        
        # Check for key log messages
        log_text = caplog.text
        assert 'Starting batch processing' in log_text or result['total_files'] == 0
        assert 'complete' in log_text.lower() or result['total_files'] == 0
    
    def test_generate_batch_zero_files(self, temp_dir):
        """Test batch processing when no files match pattern."""
        # Create empty directory
        empty_dir = os.path.join(temp_dir, 'no_match')
        os.makedirs(empty_dir)
        
        # Add a non-CSV file
        with open(os.path.join(empty_dir, 'readme.txt'), 'w') as f:
            f.write('test')
        
        pipeline = ReportPipeline(output_dir=temp_dir)
        result = pipeline.generate_batch(empty_dir, pattern='*.csv')
        
        assert result['total_files'] == 0
        assert result['successful'] == 0
        assert result['failed'] == 0
        assert result['reports'] == []
        assert result['errors'] == []

