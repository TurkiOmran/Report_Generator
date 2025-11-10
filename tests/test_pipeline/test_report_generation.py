"""
Tests for Single File Report Generation

Tests the complete workflow from CSV input to HTML report output
using real CSV files from Phase 1.
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.pipeline.report_pipeline import (
    ReportPipeline,
    ValidationError,
    MetricsCalculationError,
    VisualizationError,
    AnalysisError,
    ReportGenerationError
)


class TestReportGeneration:
    """Test suite for end-to-end report generation."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test outputs."""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)
    
    @pytest.fixture
    def sample_csv(self):
        """Path to sample CSV file from Phase 1."""
        return 'tests/fixtures/r2_39_2025-08-28T09_40_10.csv'
    
    def test_generate_report_complete_workflow(self, temp_dir, sample_csv):
        """Test complete report generation workflow without Claude API."""
        pipeline = ReportPipeline(
            output_dir=temp_dir,
            enable_analysis=False  # Skip Claude API for unit test
        )
        
        result = pipeline.generate_report(sample_csv)
        
        # Verify success
        assert result['success'] is True
        assert 'report_path' in result
        assert 'metrics' in result
        assert 'metadata' in result
        assert result['analysis_included'] is False
        
        # Verify report file exists
        assert os.path.exists(result['report_path'])
        
        # Verify report contains expected content
        with open(result['report_path'], 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert '<!DOCTYPE html>' in content
        assert 'Power Profile Test Report' in content
        assert 'r2_39' in content  # Test ID from filename
        
        # Verify statistics updated
        stats = pipeline.get_stats()
        assert stats['total_processed'] == 1
        assert stats['successful'] == 1
        assert stats['failed'] == 0
    
    def test_generate_report_with_custom_output_dir(self, temp_dir, sample_csv):
        """Test report generation with custom output directory."""
        custom_dir = os.path.join(temp_dir, 'custom_reports')
        
        pipeline = ReportPipeline(output_dir=temp_dir, enable_analysis=False)
        result = pipeline.generate_report(sample_csv, output_dir=custom_dir)
        
        assert result['success'] is True
        assert custom_dir in result['report_path']
        assert os.path.exists(custom_dir)
    
    def test_generate_report_updates_stats(self, temp_dir, sample_csv):
        """Test that generate_report updates pipeline statistics."""
        pipeline = ReportPipeline(output_dir=temp_dir, enable_analysis=False)
        
        initial_stats = pipeline.get_stats()
        assert initial_stats['total_processed'] == 0
        
        result = pipeline.generate_report(sample_csv)
        
        final_stats = pipeline.get_stats()
        assert final_stats['total_processed'] == 1
        assert final_stats['successful'] == 1
    
    def test_generate_report_includes_metrics(self, temp_dir, sample_csv):
        """Test that generated report includes calculated metrics."""
        pipeline = ReportPipeline(output_dir=temp_dir, enable_analysis=False)
        
        result = pipeline.generate_report(sample_csv)
        
        assert result['success'] is True
        metrics = result['metrics']
        
        # Verify key metrics are present
        assert 'start_power' in metrics
        assert 'target_power' in metrics
        assert 'step_direction' in metrics
        
        # Verify metrics have expected structure from Phase 1
        assert 'median' in metrics['start_power'] or 'value' in metrics['start_power']
        assert 'before' in metrics['target_power']
        assert 'after' in metrics['target_power']
    
    def test_generate_report_includes_metadata(self, temp_dir, sample_csv):
        """Test that generated report includes file metadata."""
        pipeline = ReportPipeline(output_dir=temp_dir, enable_analysis=False)
        
        result = pipeline.generate_report(sample_csv)
        
        assert result['success'] is True
        metadata = result['metadata']
        
        # Verify metadata includes key fields from Phase 1
        assert 'filename' in metadata
        assert 'total_rows' in metadata or 'total_samples' in metadata
        assert 'processing_time_seconds' in metadata or 'duration_seconds' in metadata
    
    def test_generate_report_measures_duration(self, temp_dir, sample_csv):
        """Test that generate_report measures execution duration."""
        pipeline = ReportPipeline(output_dir=temp_dir, enable_analysis=False)
        
        result = pipeline.generate_report(sample_csv)
        
        assert 'duration_seconds' in result
        assert result['duration_seconds'] > 0
        assert result['duration_seconds'] < 30  # Should be fast without Claude API
    
    def test_generate_report_invalid_file_path(self, temp_dir):
        """Test report generation with non-existent file."""
        pipeline = ReportPipeline(output_dir=temp_dir)
        
        result = pipeline.generate_report('/nonexistent/file.csv')
        
        assert result['success'] is False
        assert 'error' in result
        assert 'ValidationError' in result['error']
        
        # Verify stats updated correctly
        stats = pipeline.get_stats()
        assert stats['total_processed'] == 1
        assert stats['failed'] == 1
        assert len(stats['errors']) == 1
    
    def test_generate_report_empty_file_path(self, temp_dir):
        """Test report generation with empty file path."""
        pipeline = ReportPipeline(output_dir=temp_dir)
        
        result = pipeline.generate_report('')
        
        assert result['success'] is False
        assert 'ValidationError' in result['error']
        assert 'cannot be empty' in result['error']
    
    def test_generate_report_non_csv_file(self, temp_dir):
        """Test report generation with non-CSV file."""
        # Create a non-CSV file
        txt_file = os.path.join(temp_dir, 'test.txt')
        with open(txt_file, 'w') as f:
            f.write('test content')
        
        pipeline = ReportPipeline(output_dir=temp_dir)
        result = pipeline.generate_report(txt_file)
        
        assert result['success'] is False
        assert 'CSV file' in result['error']
    
    def test_generate_report_with_analysis_mocked(self, temp_dir, sample_csv):
        """Test report generation with mocked Claude API analysis."""
        pipeline = ReportPipeline(
            output_dir=temp_dir,
            enable_analysis=True
        )
        
        # Mock the Claude API call
        with patch('src.pipeline.report_pipeline.get_analysis') as mock_analysis:
            mock_analysis.return_value = {
                'analysis': 'This is a test analysis.',
                'tokens_used': {'total': 100, 'input': 50, 'output': 50},
                'model': 'claude-sonnet-4',
                'stop_reason': 'end_turn'
            }
            
            result = pipeline.generate_report(sample_csv)
        
        assert result['success'] is True
        assert result['analysis_included'] is True
        
        # Verify report contains analysis
        with open(result['report_path'], 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'This is a test analysis' in content
    
    def test_generate_report_analysis_failure_continues(self, temp_dir, sample_csv):
        """Test that analysis failure doesn't stop report generation."""
        pipeline = ReportPipeline(
            output_dir=temp_dir,
            enable_analysis=True
        )
        
        # Mock Claude API to raise error
        with patch('src.pipeline.report_pipeline.get_analysis') as mock_analysis:
            mock_analysis.side_effect = Exception("API Error")
            
            result = pipeline.generate_report(sample_csv)
        
        # Should still succeed without analysis
        assert result['success'] is True
        assert result['analysis_included'] is False
    
    def test_validate_input_file_directory(self, temp_dir):
        """Test that _validate_input_file rejects directories."""
        pipeline = ReportPipeline(output_dir=temp_dir)
        
        with pytest.raises(ValidationError, match="not a file"):
            pipeline._validate_input_file(temp_dir)
    
    def test_validate_input_file_success(self, temp_dir, sample_csv):
        """Test that _validate_input_file accepts valid CSV."""
        pipeline = ReportPipeline(output_dir=temp_dir)
        
        # Should not raise exception
        pipeline._validate_input_file(sample_csv)
    
    def test_calculate_metrics_success(self, temp_dir, sample_csv):
        """Test _calculate_metrics with valid CSV."""
        pipeline = ReportPipeline(output_dir=temp_dir)
        
        result = pipeline._calculate_metrics(sample_csv)
        
        assert 'metrics' in result
        assert 'metadata' in result
        assert 'raw_data' in result
        assert len(result['metrics']) > 0
    
    def test_generate_visualization_success(self, temp_dir, sample_csv):
        """Test _generate_visualization creates valid HTML."""
        pipeline = ReportPipeline(output_dir=temp_dir)
        
        # First calculate metrics
        orchestrator_result = pipeline._calculate_metrics(sample_csv)
        
        # Generate visualization
        chart_html = pipeline._generate_visualization(orchestrator_result)
        
        assert chart_html
        assert isinstance(chart_html, str)
        assert '<div' in chart_html or '<script' in chart_html
    
    def test_save_report_success(self, temp_dir, sample_csv):
        """Test _save_report creates file successfully."""
        pipeline = ReportPipeline(output_dir=temp_dir)
        
        # Prepare data
        orchestrator_result = pipeline._calculate_metrics(sample_csv)
        chart_html = pipeline._generate_visualization(orchestrator_result)
        
        # Save report
        report_path = pipeline._save_report(
            orchestrator_result,
            chart_html,
            None,  # No analysis
            temp_dir
        )
        
        assert os.path.exists(report_path)
        assert report_path.endswith('.html')
    
    def test_multiple_reports_sequential(self, temp_dir, sample_csv):
        """Test generating multiple reports sequentially."""
        pipeline = ReportPipeline(output_dir=temp_dir, enable_analysis=False)
        
        # Generate first report
        result1 = pipeline.generate_report(sample_csv)
        assert result1['success'] is True
        
        # Generate second report (same file)
        result2 = pipeline.generate_report(sample_csv)
        assert result2['success'] is True
        
        # Verify stats
        stats = pipeline.get_stats()
        assert stats['total_processed'] == 2
        assert stats['successful'] == 2
    
    def test_report_file_naming_from_csv(self, temp_dir, sample_csv):
        """Test that report filename is properly generated."""
        pipeline = ReportPipeline(output_dir=temp_dir, enable_analysis=False)
        
        result = pipeline.generate_report(sample_csv)
        
        report_filename = os.path.basename(result['report_path'])
        
        # Verify proper filename structure
        assert report_filename.startswith('report_')
        assert report_filename.endswith('.html')
        
        # Verify report was saved
        assert os.path.exists(result['report_path'])

