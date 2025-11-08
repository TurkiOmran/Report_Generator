"""
Unit tests for basic_metrics module (METRIC 1 and METRIC 2)

Tests follow the validation requirements from:
R_Test_Metrics_Complete_Pseudocode_v3.md
"""

import pytest
import pandas as pd
import numpy as np
from src.metrics.basic_metrics import BasicMetrics


class TestMetric1StartPower:
    """Tests for METRIC 1: Start Power calculation"""
    
    def test_normal_case(self):
        """Test start power with clean, consistent pre-action data"""
        df = pd.DataFrame({
            'seconds': [-60, -50, -40, -30, -20, -10, 0, 10, 20, 30],
            'mode_power': [3500] * 5 + [3600] * 5,
            'summary_wattage': [3450, 3455, 3460, 3458, 3462, 3465, 3590, 3595, 3600, 3598],
            'temp_hash_board_max': [65] * 10,
            'psu_temp_max': [45] * 10,
            'outage': [False] * 10
        })
        
        metrics = BasicMetrics(df, action_idx=5)
        result = metrics.calculate_start_power()
        
        # Validate structure
        assert 'median' in result
        assert 'last_value' in result
        assert 'difference' in result
        assert 'note' in result
        
        # Validate values
        assert result['median'] == pytest.approx(3458.0, abs=1)  # median of [3450, 3455, 3460, 3458, 3462]
        assert result['last_value'] == 3462.0
        assert result['difference'] is not None
        assert result['difference'] < 50  # Should be small difference
        assert result['note'] is None  # No warning for small difference
    
    def test_high_variance_data(self):
        """Test start power with varying pre-action values"""
        df = pd.DataFrame({
            'seconds': [-60, -50, -40, -30, -20, -10, 0, 10, 20],
            'mode_power': [3500] * 6 + [3600] * 3,
            'summary_wattage': [3400, 3450, 3500, 3480, 3520, 3470, 3590, 3595, 3600],
            'temp_hash_board_max': [65] * 9,
            'psu_temp_max': [45] * 9,
            'outage': [False] * 9
        })
        
        metrics = BasicMetrics(df, action_idx=6)
        result = metrics.calculate_start_power()
        
        # Median should be middle value
        expected_median = np.median([3400, 3450, 3500, 3480, 3520, 3470])
        assert result['median'] == pytest.approx(expected_median, abs=1)
        assert result['last_value'] == 3470.0
    
    def test_last_value_nan(self):
        """Test start power when last value before action is NaN"""
        df = pd.DataFrame({
            'seconds': [-60, -50, -40, -30, -20, -10, 0, 10, 20],
            'mode_power': [3500] * 6 + [3600] * 3,
            'summary_wattage': [3450, 3455, 3460, 3458, 3462, np.nan, 3590, 3595, 3600],
            'temp_hash_board_max': [65] * 9,
            'psu_temp_max': [45] * 9,
            'outage': [False] * 9
        })
        
        metrics = BasicMetrics(df, action_idx=6)
        result = metrics.calculate_start_power()
        
        # Should compute median from valid values only
        expected_median = np.median([3450, 3455, 3460, 3458, 3462])
        assert result['median'] == pytest.approx(expected_median, abs=1)
        assert result['last_value'] is None
        assert result['difference'] is None
        assert result['note'] == "Last value unavailable (NaN)"
    
    def test_large_difference_warning(self):
        """Test start power when last value differs significantly from median"""
        df = pd.DataFrame({
            'seconds': [-60, -50, -40, -30, -20, -10, 0, 10, 20],
            'mode_power': [3500] * 6 + [3600] * 3,
            'summary_wattage': [3450, 3455, 3460, 3458, 3462, 3550, 3590, 3595, 3600],
            'temp_hash_board_max': [65] * 9,
            'psu_temp_max': [45] * 9,
            'outage': [False] * 9
        })
        
        metrics = BasicMetrics(df, action_idx=6)
        result = metrics.calculate_start_power()
        
        # Last value (3550) differs by ~90W from median (~3458)
        assert result['difference'] > 50
        assert result['note'] is not None
        assert "differs from median" in result['note']
    
    def test_all_nan_values(self):
        """Test start power when all pre-action wattage values are NaN"""
        df = pd.DataFrame({
            'seconds': [-60, -50, -40, -30, -20, -10, 0, 10, 20],
            'mode_power': [3500] * 6 + [3600] * 3,
            'summary_wattage': [np.nan] * 6 + [3590, 3595, 3600],
            'temp_hash_board_max': [65] * 9,
            'psu_temp_max': [45] * 9,
            'outage': [True] * 6 + [False] * 3
        })
        
        metrics = BasicMetrics(df, action_idx=6)
        
        with pytest.raises(ValueError, match="All pre-action wattage values are NaN"):
            metrics.calculate_start_power()
    
    def test_no_pre_action_data(self):
        """Test start power when no pre-action data exists"""
        df = pd.DataFrame({
            'seconds': [0, 10, 20, 30],
            'mode_power': [3600] * 4,
            'summary_wattage': [3590, 3595, 3600, 3598],
            'temp_hash_board_max': [65] * 4,
            'psu_temp_max': [45] * 4,
            'outage': [False] * 4
        })
        
        metrics = BasicMetrics(df, action_idx=0)
        
        with pytest.raises(ValueError, match="No pre-action data available"):
            metrics.calculate_start_power()
    
    def test_partial_nan_values(self):
        """Test start power with some NaN values in pre-action period"""
        df = pd.DataFrame({
            'seconds': [-60, -50, -40, -30, -20, -10, 0, 10, 20],
            'mode_power': [3500] * 6 + [3600] * 3,
            'summary_wattage': [3450, np.nan, 3460, 3458, np.nan, 3462, 3590, 3595, 3600],
            'temp_hash_board_max': [65] * 9,
            'psu_temp_max': [45] * 9,
            'outage': [False, True, False, False, True, False, False, False, False]
        })
        
        metrics = BasicMetrics(df, action_idx=6)
        result = metrics.calculate_start_power()
        
        # Should compute from valid values: [3450, 3460, 3458, 3462]
        expected_median = np.median([3450, 3460, 3458, 3462])
        assert result['median'] == pytest.approx(expected_median, abs=1)


class TestMetric2TargetPower:
    """Tests for METRIC 2: Target Power extraction"""
    
    def test_normal_power_up_transition(self):
        """Test target power with normal upward step"""
        df = pd.DataFrame({
            'seconds': [-60, -50, -40, -30, -20, -10, 0, 10, 20, 30],
            'mode_power': [3500] * 6 + [3600] * 4,
            'summary_wattage': [3450, 3455, 3460, 3458, 3462, 3465, 3520, 3550, 3590, 3595],
            'temp_hash_board_max': [65] * 10,
            'psu_temp_max': [45] * 10,
            'outage': [False] * 10
        })
        
        metrics = BasicMetrics(df, action_idx=6)
        result = metrics.calculate_target_power()
        
        # Validate structure
        assert 'before' in result
        assert 'after' in result
        assert 'change' in result
        
        # Validate values
        assert result['before'] == 3500.0
        assert result['after'] == 3600.0
        assert result['change'] == 100.0
    
    def test_normal_power_down_transition(self):
        """Test target power with normal downward step"""
        df = pd.DataFrame({
            'seconds': [-60, -50, -40, -30, -20, -10, 0, 10, 20, 30],
            'mode_power': [3600] * 6 + [3500] * 4,
            'summary_wattage': [3550, 3555, 3560, 3558, 3562, 3565, 3520, 3510, 3505, 3502],
            'temp_hash_board_max': [65] * 10,
            'psu_temp_max': [45] * 10,
            'outage': [False] * 10
        })
        
        metrics = BasicMetrics(df, action_idx=6)
        result = metrics.calculate_target_power()
        
        assert result['before'] == 3600.0
        assert result['after'] == 3500.0
        assert result['change'] == -100.0
    
    def test_no_change_warning(self, caplog):
        """Test target power when no change occurs (should log warning)"""
        df = pd.DataFrame({
            'seconds': [-60, -50, -40, -30, -20, -10, 0, 10, 20, 30],
            'mode_power': [3500] * 10,
            'summary_wattage': [3450, 3455, 3460, 3458, 3462, 3465, 3468, 3470, 3472, 3475],
            'temp_hash_board_max': [65] * 10,
            'psu_temp_max': [45] * 10,
            'outage': [False] * 10
        })
        
        metrics = BasicMetrics(df, action_idx=6)
        
        with caplog.at_level('WARNING'):
            result = metrics.calculate_target_power()
        
        assert result['before'] == 3500.0
        assert result['after'] == 3500.0
        assert result['change'] == 0.0
        assert "Target power did not change" in caplog.text
    
    def test_target_changes_during_test(self, caplog):
        """Test target power when it changes during post-action period (should warn)"""
        df = pd.DataFrame({
            'seconds': [-60, -50, -40, -30, -20, -10, 0, 10, 20, 30],
            'mode_power': [3500] * 6 + [3600, 3600, 3650, 3650],
            'summary_wattage': [3450, 3455, 3460, 3458, 3462, 3465, 3520, 3550, 3590, 3595],
            'temp_hash_board_max': [65] * 10,
            'psu_temp_max': [45] * 10,
            'outage': [False] * 10
        })
        
        metrics = BasicMetrics(df, action_idx=6)
        
        with caplog.at_level('WARNING'):
            result = metrics.calculate_target_power()
        
        # Should use first post-action target (canonical)
        assert result['before'] == 3500.0
        assert result['after'] == 3600.0
        assert result['change'] == 100.0
        assert "Target changed during test" in caplog.text
    
    def test_negative_target_warning(self, caplog):
        """Test target power with negative values (should warn)"""
        df = pd.DataFrame({
            'seconds': [-60, -50, -40, -30, -20, -10, 0, 10, 20, 30],
            'mode_power': [-100] * 6 + [3600] * 4,
            'summary_wattage': [3450, 3455, 3460, 3458, 3462, 3465, 3520, 3550, 3590, 3595],
            'temp_hash_board_max': [65] * 10,
            'psu_temp_max': [45] * 10,
            'outage': [False] * 10
        })
        
        metrics = BasicMetrics(df, action_idx=6)
        
        with caplog.at_level('WARNING'):
            result = metrics.calculate_target_power()
        
        assert result['before'] == -100.0
        assert "Negative target power detected" in caplog.text
    
    def test_unusually_high_target_warning(self, caplog):
        """Test target power with unreasonably high values (should warn)"""
        df = pd.DataFrame({
            'seconds': [-60, -50, -40, -30, -20, -10, 0, 10, 20, 30],
            'mode_power': [15000] * 10,
            'summary_wattage': [14950, 14955, 14960, 14958, 14962, 14965, 14968, 14970, 14972, 14975],
            'temp_hash_board_max': [65] * 10,
            'psu_temp_max': [45] * 10,
            'outage': [False] * 10
        })
        
        metrics = BasicMetrics(df, action_idx=6)
        
        with caplog.at_level('WARNING'):
            result = metrics.calculate_target_power()
        
        assert result['before'] == 15000.0
        assert result['after'] == 15000.0
        assert "Unusually high target power detected" in caplog.text
    
    def test_nan_target_error(self):
        """Test target power when values are NaN (data corruption)"""
        df = pd.DataFrame({
            'seconds': [-60, -50, -40, -30, -20, -10, 0, 10, 20, 30],
            'mode_power': [3500] * 5 + [np.nan] + [3600] * 4,
            'summary_wattage': [3450, 3455, 3460, 3458, 3462, 3465, 3520, 3550, 3590, 3595],
            'temp_hash_board_max': [65] * 10,
            'psu_temp_max': [45] * 10,
            'outage': [False] * 10
        })
        
        metrics = BasicMetrics(df, action_idx=6)
        
        with pytest.raises(ValueError, match="Target power values are NaN"):
            metrics.calculate_target_power()
    
    def test_large_power_change(self):
        """Test target power with large step change"""
        df = pd.DataFrame({
            'seconds': [-60, -50, -40, -30, -20, -10, 0, 10, 20, 30],
            'mode_power': [1000] * 6 + [3500] * 4,
            'summary_wattage': [990, 995, 1000, 998, 1002, 1005, 1200, 1800, 2500, 3200],
            'temp_hash_board_max': [55] * 6 + [60, 65, 70, 75],
            'psu_temp_max': [35] * 6 + [40, 45, 50, 55],
            'outage': [False] * 10
        })
        
        metrics = BasicMetrics(df, action_idx=6)
        result = metrics.calculate_target_power()
        
        assert result['before'] == 1000.0
        assert result['after'] == 3500.0
        assert result['change'] == 2500.0


class TestBasicMetricsIntegration:
    """Integration tests using real data patterns"""
    
    def test_with_real_data_pattern_power_up(self):
        """Test both metrics with realistic power-up scenario"""
        # Simulates r2 file pattern: 1000W -> 3500W
        df = pd.DataFrame({
            'seconds': list(range(-60, 600, 10)),
            'mode_power': [1000] * 6 + [3500] * 60,
            'summary_wattage': [1020] * 6 + list(range(1050, 3450, 40)),
            'temp_hash_board_max': [50] * 66,
            'psu_temp_max': [35] * 66,
            'outage': [False] * 66
        })
        
        metrics = BasicMetrics(df, action_idx=6)
        
        start_power = metrics.calculate_start_power()
        target_power = metrics.calculate_target_power()
        
        # Validate start power
        assert start_power['median'] == 1020.0
        assert start_power['last_value'] == 1020.0
        assert start_power['difference'] == 0.0
        
        # Validate target power
        assert target_power['before'] == 1000.0
        assert target_power['after'] == 3500.0
        assert target_power['change'] == 2500.0
    
    def test_with_real_data_pattern_power_down(self):
        """Test both metrics with realistic power-down scenario"""
        # Simulates r9 file pattern: 3500W -> 2500W
        seconds = list(range(-60, 600, 10))
        n_rows = len(seconds)
        df = pd.DataFrame({
            'seconds': seconds,
            'mode_power': [3500] * 6 + [2500] * (n_rows - 6),
            'summary_wattage': [3450] * 6 + [3400 - (i * 15) for i in range(n_rows - 6)],
            'temp_hash_board_max': [70] * n_rows,
            'psu_temp_max': [50] * n_rows,
            'outage': [False] * n_rows
        })
        
        metrics = BasicMetrics(df, action_idx=6)
        
        start_power = metrics.calculate_start_power()
        target_power = metrics.calculate_target_power()
        
        # Validate start power
        assert start_power['median'] == 3450.0
        assert start_power['last_value'] == 3450.0
        
        # Validate target power
        assert target_power['before'] == 3500.0
        assert target_power['after'] == 2500.0
        assert target_power['change'] == -1000.0

