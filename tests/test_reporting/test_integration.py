"""
Integration Tests for Complete Reporting Flow

Tests the full reporting pipeline from metrics to HTML export.
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path

from src.reporting.metrics_formatter import format_metrics_table
from src.reporting.html_generator import generate_html_report
from src.reporting.file_exporter import save_report
from src.visualization.plotter import figure_to_html


class TestReportingIntegration:
    """Integration tests for complete reporting pipeline."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test outputs."""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)
    
    @pytest.fixture
    def sample_metrics(self):
        """Complete set of sample metrics from Phase 1."""
        return {
            'start_power': {'value': 1000.5},
            'target_power': {'before': 1000, 'after': 3500},
            'step_direction': {'direction': 'UP-STEP', 'magnitude': 2500},
            'temperature_ranges': {
                'hash_board_max': {'min': 45.2, 'max': 78.9},
                'psu_temp_max': {'min': 42.1, 'max': 65.3}
            },
            'band_entry': {
                'entered': True,
                'time': 12.5,
                'target_power': 3500
            },
            'setpoint_hit': {
                'hit': True,
                'time': 15.2,
                'target_power': 3500
            },
            'stable_plateau': {
                'achieved': True,
                'start_time': 45.0,
                'duration': 30.5
            },
            'sharp_drops': {
                'count': 2,
                'details': [
                    {'time': 10.5, 'magnitude': -250},
                    {'time': 25.3, 'magnitude': -300}
                ]
            },
            'sharp_rises': {
                'count': 1,
                'details': [
                    {'time': 35.2, 'magnitude': 220}
                ]
            },
            'overshoot_undershoot': {
                'detected': True,
                'type': 'OVERSHOOT',
                'time': 8.5,
                'magnitude': 200
            }
        }
    
    @pytest.fixture
    def sample_metadata(self):
        """Sample metadata for report."""
        return {
            'filename': 'r2_39_2025-08-28T09_40_10.csv',
            'test_id': 'r2_39',
            'miner_number': '39',
            'timestamp': '2025-08-28T09:40:10',
            'total_samples': 1234,
            'duration_seconds': 456.7,
            'step_direction': 'UP-STEP'
        }
    
    def test_complete_report_generation_flow(self, temp_dir, sample_metrics, sample_metadata):
        """Test complete flow from metrics to saved HTML report."""
        # Step 1: Format metrics
        metrics_html = format_metrics_table(sample_metrics)
        assert metrics_html
        assert 'Basic Metrics' in metrics_html
        assert 'Time-Based Metrics' in metrics_html
        assert 'Anomaly Detection' in metrics_html
        
        # Step 2: Create mock chart HTML
        chart_html = '<div id="mock-chart">Mock Plotly Chart</div>'
        
        # Step 3: Create analysis text
        analysis_text = """This is a sample analysis of the power profile test.

The miner successfully transitioned from 1000W to 3500W in an UP-STEP test."""
        
        # Step 4: Generate complete HTML report
        html_report = generate_html_report(
            metrics=sample_metrics,
            metadata=sample_metadata,
            chart_html=chart_html,
            analysis_text=analysis_text
        )
        
        assert html_report
        assert '<!DOCTYPE html>' in html_report
        assert 'Power Profile Test Report' in html_report
        assert 'r2_39' in html_report
        assert 'Mock Plotly Chart' in html_report
        
        # Step 5: Save report to disk
        file_path = save_report(
            html_content=html_report,
            output_dir=temp_dir,
            metadata=sample_metadata
        )
        
        assert os.path.exists(file_path)
        assert 'report_r2_39' in file_path
        
        # Step 6: Verify saved file content
        with open(file_path, 'r', encoding='utf-8') as f:
            saved_content = f.read()
        
        assert saved_content == html_report
        assert '1000.5 W' in saved_content  # Start power
        assert '1000 W → 3500 W' in saved_content  # Target power
        assert 'UP-STEP' in saved_content
    
    def test_report_generation_without_analysis(self, temp_dir, sample_metrics, sample_metadata):
        """Test report generation when analysis is not available."""
        chart_html = '<div id="mock-chart">Mock Chart</div>'
        
        html_report = generate_html_report(
            metrics=sample_metrics,
            metadata=sample_metadata,
            chart_html=chart_html,
            analysis_text=None
        )
        
        # Should not have analysis section
        assert 'AI Analysis' not in html_report
        
        # But should have other sections
        assert 'Performance Metrics' in html_report
        assert 'Power Timeline' in html_report
        
        # Save and verify
        file_path = save_report(html_report, output_dir=temp_dir, metadata=sample_metadata)
        assert os.path.exists(file_path)
    
    def test_report_with_minimal_metrics(self, temp_dir, sample_metadata):
        """Test report generation with minimal metrics."""
        minimal_metrics = {
            'start_power': {'value': 1000.0},
            'target_power': {'before': 1000, 'after': 3500}
        }
        
        chart_html = '<div>Chart</div>'
        
        html_report = generate_html_report(
            metrics=minimal_metrics,
            metadata=sample_metadata,
            chart_html=chart_html
        )
        
        assert html_report
        assert '1000.0 W' in html_report
        assert '1000 W → 3500 W' in html_report
        
        file_path = save_report(html_report, output_dir=temp_dir, filename='minimal_report')
        assert os.path.exists(file_path)
    
    def test_report_portability(self, temp_dir, sample_metrics, sample_metadata):
        """Test that generated report is a single portable file."""
        chart_html = '<div id="chart">Embedded Chart</div>'
        
        html_report = generate_html_report(
            metrics=sample_metrics,
            metadata=sample_metadata,
            chart_html=chart_html
        )
        
        file_path = save_report(html_report, output_dir=temp_dir, metadata=sample_metadata)
        
        # Move file to different location
        new_dir = os.path.join(temp_dir, 'moved')
        os.makedirs(new_dir)
        new_path = os.path.join(new_dir, os.path.basename(file_path))
        shutil.move(file_path, new_path)
        
        # File should still be readable and complete
        assert os.path.exists(new_path)
        with open(new_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert '<!DOCTYPE html>' in content
        assert '<style>' in content  # Embedded CSS
        assert 'Power Profile Test Report' in content
    
    def test_unicode_handling_throughout_pipeline(self, temp_dir):
        """Test that Unicode characters are preserved through entire pipeline."""
        metrics = {
            'start_power': {'value': 1000.0},
            'temperature_ranges': {
                'hash_board_max': {'min': 45.2, 'max': 78.9},
                'psu_temp_max': {'min': 42.1, 'max': 65.3}
            }
        }
        
        metadata = {
            'filename': 'test.csv',
            'test_id': 'r1_39',
            'timestamp': '2025-11-10T12:00:00'
        }
        
        chart_html = '<div>Chart with °C</div>'
        analysis = "Temperature reached 78.9°C → System stable ✓"
        
        html_report = generate_html_report(
            metrics=metrics,
            metadata=metadata,
            chart_html=chart_html,
            analysis_text=analysis
        )
        
        file_path = save_report(html_report, output_dir=temp_dir, metadata=metadata)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert '°C' in content
        assert '→' in content
        assert '✓' in content

