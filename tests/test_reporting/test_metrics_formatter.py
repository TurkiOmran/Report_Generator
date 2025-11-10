"""
Tests for Metrics Formatter Module

Validates HTML table generation from metrics dictionaries with:
- All 10 metric types
- Proper categorization
- Numeric formatting
- Detailed list rendering
- Edge cases (missing metrics, empty data)
"""

import pytest
from src.reporting.metrics_formatter import (
    format_metrics_table,
    _extract_basic_metrics,
    _extract_time_metrics,
    _extract_anomaly_metrics,
    _format_anomaly_details,
    _format_category_section
)


class TestMetricsFormatter:
    """Test suite for metrics formatter functions."""
    
    def test_format_empty_metrics(self):
        """Test handling of empty metrics dictionary."""
        html = format_metrics_table({})
        assert 'no-data' in html.lower() or 'no metrics' in html.lower()
    
    def test_format_complete_metrics(self):
        """Test formatting with all 10 metrics present."""
        metrics = {
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
        
        html = format_metrics_table(metrics)
        
        # Verify all categories present
        assert 'Basic Metrics' in html
        assert 'Time-Based Metrics' in html
        assert 'Anomaly Detection' in html
        
        # Verify key metric values
        assert '1000.5 W' in html  # Start power
        assert '1000 W → 3500 W' in html  # Target power
        assert 'UP-STEP' in html  # Direction
        assert '45.2°C' in html  # Temperature
        assert 't=12.5s' in html  # Band entry
        assert 't=15.2s' in html  # Setpoint
        assert 't=45.0s' in html  # Plateau
        assert '2 drop(s)' in html  # Sharp drops
        assert '1 rise(s)' in html  # Sharp rises
        assert 'OVERSHOOT' in html  # Overshoot
        
        # Verify HTML structure
        assert '<table class="metrics-table">' in html
        assert '<th class="metric-name">' in html
        assert '<th class="metric-value">' in html
        assert '<th class="metric-description">' in html
    
    def test_extract_basic_metrics_complete(self):
        """Test extraction of all 4 basic metrics."""
        metrics = {
            'start_power': {'value': 1000.5},
            'target_power': {'before': 1000, 'after': 3500},
            'step_direction': {'direction': 'DOWN-STEP', 'magnitude': -2500},
            'temperature_ranges': {
                'hash_board_max': {'min': 45.0, 'max': 75.0},
                'psu_temp_max': {'min': 40.0, 'max': 60.0}
            }
        }
        
        rows = _extract_basic_metrics(metrics)
        
        assert len(rows) == 4
        assert rows[0]['name'] == 'Start Power'
        assert '1000.5 W' in rows[0]['value']
        assert rows[1]['name'] == 'Target Power'
        assert '1000 W → 3500 W' in rows[1]['value']
        assert rows[2]['name'] == 'Step Direction'
        assert 'DOWN-STEP' in rows[2]['value']
        assert rows[3]['name'] == 'Temperature Ranges'
        assert 'Hash Board' in rows[3]['value']
        assert 'PSU' in rows[3]['value']
    
    def test_extract_basic_metrics_partial(self):
        """Test extraction with only some basic metrics."""
        metrics = {
            'start_power': {'value': 1500.0},
            'step_direction': {'direction': 'UP-STEP', 'magnitude': 1000}
        }
        
        rows = _extract_basic_metrics(metrics)
        
        assert len(rows) == 2
        assert rows[0]['name'] == 'Start Power'
        assert rows[1]['name'] == 'Step Direction'
    
    def test_extract_time_metrics_all_success(self):
        """Test time metrics when all criteria met."""
        metrics = {
            'band_entry': {
                'entered': True,
                'time': 10.5,
                'target_power': 3500
            },
            'setpoint_hit': {
                'hit': True,
                'time': 12.3,
                'target_power': 3500
            },
            'stable_plateau': {
                'achieved': True,
                'start_time': 40.0,
                'duration': 35.2
            }
        }
        
        rows = _extract_time_metrics(metrics)
        
        assert len(rows) == 3
        assert '✓' in rows[0]['value']  # Band entry success
        assert 't=10.5s' in rows[0]['value']
        assert '✓' in rows[1]['value']  # Setpoint success
        assert 't=12.3s' in rows[1]['value']
        assert '✓' in rows[2]['value']  # Plateau success
        assert 't=40.0s' in rows[2]['value']
    
    def test_extract_time_metrics_all_failure(self):
        """Test time metrics when all criteria not met."""
        metrics = {
            'band_entry': {'entered': False},
            'setpoint_hit': {'hit': False},
            'stable_plateau': {'achieved': False}
        }
        
        rows = _extract_time_metrics(metrics)
        
        assert len(rows) == 3
        assert '✗' in rows[0]['value']  # Band entry failure
        assert 'Never entered' in rows[0]['value']
        assert '✗' in rows[1]['value']  # Setpoint failure
        assert 'Never hit' in rows[1]['value']
        assert '✗' in rows[2]['value']  # Plateau failure
        assert 'No stable plateau' in rows[2]['value']
    
    def test_extract_anomaly_metrics_with_details(self):
        """Test anomaly metrics with detailed event lists."""
        metrics = {
            'sharp_drops': {
                'count': 3,
                'details': [
                    {'time': 10.0, 'magnitude': -250},
                    {'time': 20.0, 'magnitude': -300},
                    {'time': 30.0, 'magnitude': -275}
                ]
            },
            'sharp_rises': {
                'count': 2,
                'details': [
                    {'time': 15.5, 'magnitude': 220},
                    {'time': 35.2, 'magnitude': 240}
                ]
            },
            'overshoot_undershoot': {
                'detected': True,
                'type': 'UNDERSHOOT',
                'time': 8.2,
                'magnitude': -180
            }
        }
        
        rows = _extract_anomaly_metrics(metrics)
        
        assert len(rows) == 3
        assert '3 drop(s)' in rows[0]['value']
        assert 't=10.0s' in rows[0]['value']
        assert '2 rise(s)' in rows[1]['value']
        assert 't=15.5s' in rows[1]['value']
        assert 'UNDERSHOOT' in rows[2]['value']
        assert 't=8.2s' in rows[2]['value']
    
    def test_extract_anomaly_metrics_no_events(self):
        """Test anomaly metrics when no anomalies detected."""
        metrics = {
            'sharp_drops': {'count': 0, 'details': []},
            'sharp_rises': {'count': 0, 'details': []},
            'overshoot_undershoot': {'detected': False}
        }
        
        rows = _extract_anomaly_metrics(metrics)
        
        assert len(rows) == 3
        assert '0 drop(s)' in rows[0]['value']
        assert '0 rise(s)' in rows[1]['value']
        assert '✗' in rows[2]['value']
    
    def test_format_anomaly_details_empty(self):
        """Test anomaly details formatting with empty list."""
        html = _format_anomaly_details([], 'drop')
        assert html == ""
    
    def test_format_anomaly_details_few_events(self):
        """Test anomaly details formatting with few events."""
        details = [
            {'time': 10.5, 'magnitude': -250},
            {'time': 20.3, 'magnitude': -300}
        ]
        
        html = _format_anomaly_details(details, 'drop')
        
        assert '<ul class="anomaly-details">' in html
        assert 't=10.5s: -250W drop' in html
        assert 't=20.3s: -300W drop' in html
        assert '</ul>' in html
    
    def test_format_anomaly_details_many_events(self):
        """Test anomaly details truncation with >10 events."""
        details = [{'time': i * 10.0, 'magnitude': -250 - i * 10} for i in range(15)]
        
        html = _format_anomaly_details(details, 'drop')
        
        # Should show first 10 and "... and 5 more"
        assert 't=0.0s' in html
        assert 't=90.0s' in html
        assert '... and 5 more' in html
    
    def test_format_category_section_empty(self):
        """Test category section with no rows."""
        html = _format_category_section('Test Category', [])
        assert html == ""
    
    def test_format_category_section_with_rows(self):
        """Test category section with multiple rows."""
        rows = [
            {
                'name': 'Metric 1',
                'value': '100 W',
                'description': 'Test metric 1'
            },
            {
                'name': 'Metric 2',
                'value': '200 W',
                'description': 'Test metric 2'
            }
        ]
        
        html = _format_category_section('Test Category', rows)
        
        assert '<h3 class="category-title">Test Category</h3>' in html
        assert '<table class="metrics-table">' in html
        assert 'Metric 1' in html
        assert '100 W' in html
        assert 'Test metric 1' in html
        assert 'Metric 2' in html
        assert '200 W' in html
    
    def test_format_metrics_partial_data(self):
        """Test formatting with only some metrics present."""
        metrics = {
            'start_power': {'value': 1000.0},
            'band_entry': {'entered': True, 'time': 10.0},
            'sharp_drops': {'count': 1, 'details': [{'time': 5.0, 'magnitude': -250}]}
        }
        
        html = format_metrics_table(metrics)
        
        # Should have all three categories (one metric each)
        assert 'Basic Metrics' in html
        assert 'Time-Based Metrics' in html
        assert 'Anomaly Detection' in html
        assert '1000.0 W' in html
        assert 't=10.0s' in html
        assert '1 drop(s)' in html
    
    def test_numeric_formatting_precision(self):
        """Test that numeric values are formatted with correct precision."""
        metrics = {
            'start_power': {'value': 1234.5678},
            'target_power': {'before': 1234.5678, 'after': 3456.789},
            'step_direction': {'direction': 'UP-STEP', 'magnitude': 2222.2345}
        }
        
        html = format_metrics_table(metrics)
        
        # Start power: 1 decimal
        assert '1234.6 W' in html
        # Target power: 0 decimals
        assert '1235 W → 3457 W' in html
        # Magnitude: 0 decimals (in +/- format)
        assert '+2222 W' in html
    
    def test_html_structure_validity(self):
        """Test that generated HTML has valid structure."""
        metrics = {
            'start_power': {'value': 1000.0},
            'band_entry': {'entered': True, 'time': 10.0}
        }
        
        html = format_metrics_table(metrics)
        
        # Check for proper nesting
        assert html.count('<div class="metrics-container">') == 1
        assert html.count('</div>') >= 1  # At least closing container
        assert html.count('<table class="metrics-table">') >= 1
        assert html.count('</table>') == html.count('<table class="metrics-table">')
        assert html.count('<thead>') == html.count('</thead>')
        assert html.count('<tbody>') == html.count('</tbody>')
        assert html.count('<tr>') == html.count('</tr>')

