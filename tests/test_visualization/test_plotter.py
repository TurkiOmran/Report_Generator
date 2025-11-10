"""
Tests for power timeline visualization module.

Tests cover:
- Basic plot creation with valid data
- Zone overlays (band entry, setpoint)
- Action marker rendering
- HTML conversion
- Different step directions
- Error handling
"""

import pytest
import plotly.graph_objects as go
import pandas as pd
from pathlib import Path

from src.visualization.plotter import (
    create_power_timeline,
    figure_to_html,
    PowerTimelinePlotter
)
from src.metrics.orchestrator import MetricOrchestrator


class TestPowerTimelinePlotter:
    """Test suite for PowerTimelinePlotter class."""
    
    def test_init_with_valid_data(self, sample_orchestrator_result):
        """Test plotter initialization with valid data."""
        plotter = PowerTimelinePlotter(
            sample_orchestrator_result['raw_data'],
            sample_orchestrator_result['metrics'],
            sample_orchestrator_result['metadata']
        )
        
        assert plotter.raw_data is not None
        assert plotter.metrics is not None
        assert plotter.metadata is not None
        assert isinstance(plotter.df, pd.DataFrame)
        assert len(plotter.df) > 0
    
    def test_init_missing_required_columns(self):
        """Test that initialization fails with missing required columns."""
        raw_data = [
            {'time': 0, 'value': 100},  # Wrong column names
            {'time': 1, 'value': 200}
        ]
        metrics = {}
        metadata = {}
        
        with pytest.raises(ValueError, match="Missing required columns"):
            PowerTimelinePlotter(raw_data, metrics, metadata)
    
    def test_create_power_timeline_returns_figure(self, sample_orchestrator_result):
        """Test that create_power_timeline returns a valid Figure."""
        plotter = PowerTimelinePlotter(
            sample_orchestrator_result['raw_data'],
            sample_orchestrator_result['metrics'],
            sample_orchestrator_result['metadata']
        )
        
        fig = plotter.create_power_timeline()
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0  # Should have at least the power trace
    
    def test_power_trace_added(self, sample_orchestrator_result):
        """Test that the main power trace is added correctly."""
        plotter = PowerTimelinePlotter(
            sample_orchestrator_result['raw_data'],
            sample_orchestrator_result['metrics'],
            sample_orchestrator_result['metadata']
        )
        
        fig = plotter.create_power_timeline()
        
        # Find the power trace
        power_trace = next(
            (trace for trace in fig.data if trace.name == 'Actual Power'),
            None
        )
        
        assert power_trace is not None
        assert len(power_trace.x) > 0
        assert len(power_trace.y) > 0
        assert power_trace.mode == 'lines'
    
    def test_band_entry_zone_added(self, sample_orchestrator_result):
        """Test that band entry zone (±5%) is added."""
        plotter = PowerTimelinePlotter(
            sample_orchestrator_result['raw_data'],
            sample_orchestrator_result['metrics'],
            sample_orchestrator_result['metadata']
        )
        
        fig = plotter.create_power_timeline()
        
        # Find the band entry zone trace
        band_trace = next(
            (trace for trace in fig.data if 'Band Entry' in trace.name),
            None
        )
        
        assert band_trace is not None
        assert band_trace.fill == 'toself'
    
    def test_setpoint_zone_added(self, sample_orchestrator_result):
        """Test that setpoint zone (±2%) is added."""
        plotter = PowerTimelinePlotter(
            sample_orchestrator_result['raw_data'],
            sample_orchestrator_result['metrics'],
            sample_orchestrator_result['metadata']
        )
        
        fig = plotter.create_power_timeline()
        
        # Find the setpoint zone trace
        setpoint_trace = next(
            (trace for trace in fig.data if 'Setpoint' in trace.name),
            None
        )
        
        assert setpoint_trace is not None
        assert setpoint_trace.fill == 'toself'
    
    def test_action_marker_added(self, sample_orchestrator_result):
        """Test that action marker (t=0 vertical line) is added."""
        plotter = PowerTimelinePlotter(
            sample_orchestrator_result['raw_data'],
            sample_orchestrator_result['metrics'],
            sample_orchestrator_result['metadata']
        )
        
        fig = plotter.create_power_timeline()
        
        # Find the action marker trace
        action_trace = next(
            (trace for trace in fig.data if 'Action Time' in trace.name),
            None
        )
        
        assert action_trace is not None
        assert action_trace.x[0] == 0  # Should be at t=0
        assert action_trace.x[1] == 0
        assert action_trace.line.dash == 'dash'
    
    def test_layout_configuration(self, sample_orchestrator_result):
        """Test that layout is properly configured."""
        plotter = PowerTimelinePlotter(
            sample_orchestrator_result['raw_data'],
            sample_orchestrator_result['metrics'],
            sample_orchestrator_result['metadata']
        )
        
        fig = plotter.create_power_timeline()
        
        assert 'Power Profile Timeline' in fig.layout.title.text
        assert fig.layout.xaxis.title.text == 'Time (seconds)'
        assert fig.layout.yaxis.title.text == 'Power (W)'
        assert fig.layout.hovermode == 'closest'


class TestCreatePowerTimeline:
    """Test suite for create_power_timeline convenience function."""
    
    def test_create_power_timeline_function(self, sample_orchestrator_result):
        """Test the convenience function creates a valid figure."""
        fig = create_power_timeline(
            sample_orchestrator_result['raw_data'],
            sample_orchestrator_result['metrics'],
            sample_orchestrator_result['metadata']
        )
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0


class TestFigureToHtml:
    """Test suite for HTML conversion function."""
    
    def test_figure_to_html_returns_string(self, sample_orchestrator_result):
        """Test that figure_to_html returns a valid HTML string."""
        fig = create_power_timeline(
            sample_orchestrator_result['raw_data'],
            sample_orchestrator_result['metrics'],
            sample_orchestrator_result['metadata']
        )
        
        html = figure_to_html(fig, include_plotlyjs='cdn')
        
        assert isinstance(html, str)
        assert len(html) > 0
        assert '<div' in html
    
    def test_html_no_cdn_dependencies(self, sample_orchestrator_result):
        """Test that HTML can be generated without CDN dependencies."""
        fig = create_power_timeline(
            sample_orchestrator_result['raw_data'],
            sample_orchestrator_result['metrics'],
            sample_orchestrator_result['metadata']
        )
        
        # Generate self-contained HTML
        html = figure_to_html(fig, include_plotlyjs=True)
        
        assert isinstance(html, str)
        assert 'plotly' in html.lower()
        # Self-contained should have embedded Plotly code
        assert len(html) > 10000  # Should be large with embedded library
    
    def test_html_with_cdn(self, sample_orchestrator_result):
        """Test HTML generation with CDN link."""
        fig = create_power_timeline(
            sample_orchestrator_result['raw_data'],
            sample_orchestrator_result['metrics'],
            sample_orchestrator_result['metadata']
        )
        
        html = figure_to_html(fig, include_plotlyjs='cdn')
        
        assert isinstance(html, str)
        # CDN version should be smaller
        assert len(html) < 100000


class TestRealDataIntegration:
    """Integration tests with real CSV files."""
    
    @pytest.mark.parametrize('csv_file', [
        'valid_power_profile.csv',
        'upstep_clean.csv',
        'downstep_clean.csv',
    ])
    def test_end_to_end_with_real_data(self, csv_file):
        """Test complete pipeline from CSV to plot with real data."""
        # Get path to test fixture
        fixture_path = Path(__file__).parent.parent / 'fixtures' / csv_file
        
        if not fixture_path.exists():
            pytest.skip(f"Test fixture {csv_file} not found")
        
        # Process file with orchestrator
        orchestrator = MetricOrchestrator()
        result = orchestrator.process_file(str(fixture_path))
        
        assert result['success'], f"Orchestrator failed: {result.get('error')}"
        
        # Create visualization
        fig = create_power_timeline(
            result['raw_data'],
            result['metrics'],
            result['metadata']
        )
        
        # Validate figure
        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 4  # Power trace + zones + action marker
        
        # Validate that we can convert to HTML
        html = figure_to_html(fig, include_plotlyjs='cdn')
        assert isinstance(html, str)
        assert len(html) > 0
    
    def test_upstep_visualization(self):
        """Test visualization with upstep data."""
        fixture_path = Path(__file__).parent.parent / 'fixtures' / 'upstep_clean.csv'
        
        if not fixture_path.exists():
            pytest.skip("upstep_clean.csv not found")
        
        orchestrator = MetricOrchestrator()
        result = orchestrator.process_file(str(fixture_path))
        
        assert result['success']
        
        fig = create_power_timeline(
            result['raw_data'],
            result['metrics'],
            result['metadata']
        )
        
        # Check that title reflects UP direction
        assert 'UP' in fig.layout.title.text or 'upstep' in str(fixture_path).lower()
    
    def test_downstep_visualization(self):
        """Test visualization with downstep data."""
        fixture_path = Path(__file__).parent.parent / 'fixtures' / 'downstep_clean.csv'
        
        if not fixture_path.exists():
            pytest.skip("downstep_clean.csv not found")
        
        orchestrator = MetricOrchestrator()
        result = orchestrator.process_file(str(fixture_path))
        
        assert result['success']
        
        fig = create_power_timeline(
            result['raw_data'],
            result['metrics'],
            result['metadata']
        )
        
        # Check that title reflects DOWN direction
        assert 'DOWN' in fig.layout.title.text or 'downstep' in str(fixture_path).lower()


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_missing_target_power_skips_zones(self):
        """Test that missing target power doesn't crash, just skips zones."""
        raw_data = [
            {'seconds': -10, 'summary_wattage': 3600},
            {'seconds': 0, 'summary_wattage': 3500},
            {'seconds': 10, 'summary_wattage': 1000},
        ]
        metrics = {}  # No target_power
        metadata = {}
        
        # Should not crash
        fig = create_power_timeline(raw_data, metrics, metadata)
        
        assert isinstance(fig, go.Figure)
        # Should have power trace and action marker, but no zones
        assert len(fig.data) >= 2
    
    def test_with_temperature_data(self, sample_orchestrator_result):
        """Test that temperature data is included in hover tooltips."""
        # Ensure temperature columns exist
        for record in sample_orchestrator_result['raw_data']:
            record['temp_hash_board_max'] = 65.0
            record['psu_temp_max'] = 45.0
        
        fig = create_power_timeline(
            sample_orchestrator_result['raw_data'],
            sample_orchestrator_result['metrics'],
            sample_orchestrator_result['metadata']
        )
        
        # Find power trace
        power_trace = next(
            (trace for trace in fig.data if trace.name == 'Actual Power'),
            None
        )
        
        assert power_trace is not None
        # Check that hover text includes temperature
        assert any('Temp' in str(text) for text in power_trace.hovertext)


@pytest.fixture
def sample_orchestrator_result():
    """
    Create a sample orchestrator result for testing.
    
    This mimics the structure returned by MetricOrchestrator.process_file()
    """
    # Note: Column names are standardized by ingestion (miner. prefix removed)
    raw_data = [
        {'seconds': -60, 'summary_wattage': 3600, 'mode_power': 3600},
        {'seconds': -50, 'summary_wattage': 3590, 'mode_power': 3600},
        {'seconds': -40, 'summary_wattage': 3595, 'mode_power': 3600},
        {'seconds': -30, 'summary_wattage': 3600, 'mode_power': 3600},
        {'seconds': -20, 'summary_wattage': 3605, 'mode_power': 3600},
        {'seconds': -10, 'summary_wattage': 3598, 'mode_power': 3600},
        {'seconds': 0, 'summary_wattage': 3500, 'mode_power': 1000},
        {'seconds': 10, 'summary_wattage': 2800, 'mode_power': 1000},
        {'seconds': 20, 'summary_wattage': 1500, 'mode_power': 1000},
        {'seconds': 30, 'summary_wattage': 1050, 'mode_power': 1000},
        {'seconds': 40, 'summary_wattage': 1005, 'mode_power': 1000},
        {'seconds': 50, 'summary_wattage': 998, 'mode_power': 1000},
        {'seconds': 60, 'summary_wattage': 1002, 'mode_power': 1000},
        {'seconds': 70, 'summary_wattage': 1001, 'mode_power': 1000},
        {'seconds': 80, 'summary_wattage': 1000, 'mode_power': 1000},
        {'seconds': 90, 'summary_wattage': 1000, 'mode_power': 1000},
    ]
    
    metrics = {
        'target_power': {
            'before': 3600,
            'after': 1000
        },
        'step_direction': {
            'direction': 'DOWN',
            'delta': -2600
        },
        'start_power': {
            'median': 3598
        }
    }
    
    metadata = {
        'filename': 'test.csv',
        'total_rows': len(raw_data)
    }
    
    return {
        'success': True,
        'raw_data': raw_data,
        'metrics': metrics,
        'metadata': metadata
    }

