"""
Tests for ReportPipeline Class Initialization

Validates proper initialization, configuration validation, logging setup,
and directory management.
"""

import pytest
import logging
import tempfile
import shutil
from pathlib import Path

from src.pipeline.report_pipeline import (
    ReportPipeline,
    PipelineError,
    ValidationError
)


class TestReportPipelineInit:
    """Test suite for ReportPipeline initialization."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)
    
    def test_init_default_configuration(self, temp_dir):
        """Test initialization with default configuration."""
        pipeline = ReportPipeline(output_dir=temp_dir)
        
        assert pipeline.output_dir == Path(temp_dir)
        assert pipeline.enable_analysis is True
        assert pipeline.include_plotlyjs == 'cdn'
        assert pipeline.logger is not None
        assert pipeline.stats['total_processed'] == 0
        assert pipeline.stats['successful'] == 0
        assert pipeline.stats['failed'] == 0
    
    def test_init_custom_configuration(self, temp_dir):
        """Test initialization with custom configuration."""
        pipeline = ReportPipeline(
            output_dir=temp_dir,
            enable_analysis=False,
            log_level='DEBUG',
            include_plotlyjs=True
        )
        
        assert pipeline.output_dir == Path(temp_dir)
        assert pipeline.enable_analysis is False
        assert pipeline.include_plotlyjs is True
        assert pipeline.logger.level == logging.DEBUG
    
    def test_init_creates_output_directory(self, temp_dir):
        """Test that initialization creates output directory."""
        output_path = Path(temp_dir) / 'new_reports'
        assert not output_path.exists()
        
        pipeline = ReportPipeline(output_dir=str(output_path))
        
        assert output_path.exists()
        assert output_path.is_dir()
    
    def test_init_nested_directory_creation(self, temp_dir):
        """Test initialization creates nested directories."""
        nested_path = Path(temp_dir) / 'level1' / 'level2' / 'level3'
        
        pipeline = ReportPipeline(output_dir=str(nested_path))
        
        assert nested_path.exists()
        assert nested_path.is_dir()
    
    def test_init_validates_output_dir_type(self):
        """Test that invalid output_dir type raises error."""
        with pytest.raises(ValueError, match="output_dir must be a non-empty string"):
            ReportPipeline(output_dir=None)
        
        with pytest.raises(ValueError, match="output_dir must be a non-empty string"):
            ReportPipeline(output_dir='')
        
        with pytest.raises(ValueError, match="output_dir must be a non-empty string"):
            ReportPipeline(output_dir=123)
    
    def test_init_validates_enable_analysis_type(self, temp_dir):
        """Test that invalid enable_analysis type raises error."""
        with pytest.raises(ValueError, match="enable_analysis must be a boolean"):
            ReportPipeline(output_dir=temp_dir, enable_analysis='yes')
        
        with pytest.raises(ValueError, match="enable_analysis must be a boolean"):
            ReportPipeline(output_dir=temp_dir, enable_analysis=1)
    
    def test_init_validates_log_level(self, temp_dir):
        """Test that invalid log_level raises error."""
        with pytest.raises(ValueError, match="log_level must be one of"):
            ReportPipeline(output_dir=temp_dir, log_level='INVALID')
    
    def test_init_validates_include_plotlyjs(self, temp_dir):
        """Test that invalid include_plotlyjs raises error."""
        with pytest.raises(ValueError, match="include_plotlyjs must be one of"):
            ReportPipeline(output_dir=temp_dir, include_plotlyjs='invalid')
    
    def test_init_valid_log_levels(self, temp_dir):
        """Test all valid log levels."""
        for level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            pipeline = ReportPipeline(output_dir=temp_dir, log_level=level)
            assert pipeline.logger.level == getattr(logging, level)
    
    def test_init_case_insensitive_log_level(self, temp_dir):
        """Test that log_level is case insensitive."""
        pipeline = ReportPipeline(output_dir=temp_dir, log_level='debug')
        assert pipeline.logger.level == logging.DEBUG
        
        pipeline = ReportPipeline(output_dir=temp_dir, log_level='Info')
        assert pipeline.logger.level == logging.INFO
    
    def test_logger_has_proper_formatting(self, temp_dir):
        """Test that logger has proper formatter."""
        pipeline = ReportPipeline(output_dir=temp_dir)
        
        assert len(pipeline.logger.handlers) > 0
        handler = pipeline.logger.handlers[0]
        assert handler.formatter is not None
        
        # Check format includes timestamp, name, level, and message
        format_str = handler.formatter._fmt
        assert '%(asctime)s' in format_str
        assert '%(name)s' in format_str
        assert '%(levelname)s' in format_str
        assert '%(message)s' in format_str
    
    def test_logger_no_duplicate_handlers(self, temp_dir):
        """Test that creating multiple pipelines doesn't create duplicate handlers."""
        initial_handler_count = len(logging.getLogger('src.pipeline.report_pipeline').handlers)
        
        pipeline1 = ReportPipeline(output_dir=temp_dir)
        handler_count1 = len(pipeline1.logger.handlers)
        
        pipeline2 = ReportPipeline(output_dir=temp_dir)
        handler_count2 = len(pipeline2.logger.handlers)
        
        # Should not increase with each instance
        assert handler_count2 == handler_count1
    
    def test_get_stats_initial_state(self, temp_dir):
        """Test get_stats returns correct initial state."""
        pipeline = ReportPipeline(output_dir=temp_dir)
        
        stats = pipeline.get_stats()
        
        assert stats['total_processed'] == 0
        assert stats['successful'] == 0
        assert stats['failed'] == 0
        assert stats['success_rate'] == 0
        assert stats['errors'] == []
    
    def test_get_stats_returns_copy(self, temp_dir):
        """Test that get_stats returns a copy, not reference."""
        pipeline = ReportPipeline(output_dir=temp_dir)
        
        stats1 = pipeline.get_stats()
        stats1['total_processed'] = 999
        
        stats2 = pipeline.get_stats()
        assert stats2['total_processed'] == 0  # Original unchanged
    
    def test_reset_stats(self, temp_dir):
        """Test reset_stats clears all statistics."""
        pipeline = ReportPipeline(output_dir=temp_dir)
        
        # Manually modify stats
        pipeline.stats['total_processed'] = 10
        pipeline.stats['successful'] = 7
        pipeline.stats['failed'] = 3
        pipeline.stats['errors'] = ['error1', 'error2']
        
        # Reset
        pipeline.reset_stats()
        
        # Verify reset
        assert pipeline.stats['total_processed'] == 0
        assert pipeline.stats['successful'] == 0
        assert pipeline.stats['failed'] == 0
        assert pipeline.stats['errors'] == []
    
    def test_valid_plotlyjs_options(self, temp_dir):
        """Test all valid include_plotlyjs options."""
        # Test 'cdn'
        pipeline_cdn = ReportPipeline(output_dir=temp_dir, include_plotlyjs='cdn')
        assert pipeline_cdn.include_plotlyjs == 'cdn'
        
        # Test True
        pipeline_true = ReportPipeline(output_dir=temp_dir, include_plotlyjs=True)
        assert pipeline_true.include_plotlyjs is True
        
        # Test False
        pipeline_false = ReportPipeline(output_dir=temp_dir, include_plotlyjs=False)
        assert pipeline_false.include_plotlyjs is False
    
    def test_output_dir_as_path_object(self, temp_dir):
        """Test initialization with Path object."""
        path_obj = Path(temp_dir) / 'reports'
        
        pipeline = ReportPipeline(output_dir=str(path_obj))
        
        assert pipeline.output_dir == path_obj
        assert path_obj.exists()
    
    def test_init_with_existing_directory(self, temp_dir):
        """Test initialization with pre-existing directory."""
        # Create directory first
        output_path = Path(temp_dir) / 'existing'
        output_path.mkdir()
        
        # Should not raise error
        pipeline = ReportPipeline(output_dir=str(output_path))
        
        assert output_path.exists()
        assert pipeline.output_dir == output_path
    
    def test_configuration_immutability(self, temp_dir):
        """Test that configuration is stored correctly."""
        pipeline = ReportPipeline(
            output_dir=temp_dir,
            enable_analysis=False,
            log_level='ERROR',
            include_plotlyjs=True
        )
        
        # Verify configuration is stored
        assert pipeline.output_dir == Path(temp_dir)
        assert pipeline.enable_analysis is False
        assert pipeline.include_plotlyjs is True
        assert pipeline.logger.level == logging.ERROR

