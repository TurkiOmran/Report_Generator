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


class TestMetric3StepDirection:
    """Tests for METRIC 3: Step Direction classification"""
    
    def test_up_step_large_change(self):
        """Test UP-STEP classification with large power increase"""
        df = pd.DataFrame({
            'seconds': [-60, -50, -40, -30, -20, -10, 0, 10, 20, 30],
            'mode_power': [1000] * 6 + [3500] * 4,
            'summary_wattage': [1020] * 6 + [1500, 2200, 3000, 3450],
            'temp_hash_board_max': [50] * 6 + [55, 60, 65, 70],
            'psu_temp_max': [35] * 6 + [38, 40, 42, 44],
            'outage': [False] * 10
        })
        
        metrics = BasicMetrics(df, action_idx=6)
        start_power = metrics.calculate_start_power()
        target_power = metrics.calculate_target_power()
        step_direction = metrics.calculate_step_direction(start_power, target_power)
        
        # Validate structure
        assert 'direction' in step_direction
        assert 'delta' in step_direction
        assert 'description' in step_direction
        
        # Validate classification
        assert step_direction['direction'] == "UP-STEP"
        assert step_direction['delta'] > 50  # Should be ~2480W (3500 - 1020)
        assert "Ramping up" in step_direction['description']
    
    def test_down_step_classification(self):
        """Test DOWN-STEP classification with power decrease"""
        df = pd.DataFrame({
            'seconds': [-60, -50, -40, -30, -20, -10, 0, 10, 20, 30],
            'mode_power': [3500] * 6 + [2500] * 4,
            'summary_wattage': [3450] * 6 + [3300, 3100, 2800, 2520],
            'temp_hash_board_max': [70] * 6 + [68, 65, 62, 60],
            'psu_temp_max': [45] * 6 + [44, 43, 42, 41],
            'outage': [False] * 10
        })
        
        metrics = BasicMetrics(df, action_idx=6)
        start_power = metrics.calculate_start_power()
        target_power = metrics.calculate_target_power()
        step_direction = metrics.calculate_step_direction(start_power, target_power)
        
        assert step_direction['direction'] == "DOWN-STEP"
        assert step_direction['delta'] < -50  # Should be ~-950W (2500 - 3450)
        assert "Ramping down" in step_direction['description']
        assert abs(step_direction['delta']) == pytest.approx(950, abs=10)
    
    def test_minimal_step_small_change(self, caplog):
        """Test MINIMAL-STEP classification with small change"""
        df = pd.DataFrame({
            'seconds': [-60, -50, -40, -30, -20, -10, 0, 10, 20, 30],
            'mode_power': [3500] * 6 + [3530] * 4,
            'summary_wattage': [3500] * 6 + [3510, 3515, 3520, 3525],
            'temp_hash_board_max': [65] * 10,
            'psu_temp_max': [45] * 10,
            'outage': [False] * 10
        })
        
        metrics = BasicMetrics(df, action_idx=6)
        start_power = metrics.calculate_start_power()
        target_power = metrics.calculate_target_power()
        
        with caplog.at_level('WARNING'):
            step_direction = metrics.calculate_step_direction(start_power, target_power)
        
        # delta = 3530 - 3500 = 30W, which is <= 50
        assert step_direction['direction'] == "MINIMAL-STEP"
        assert abs(step_direction['delta']) <= 50
        assert "Minimal change" in step_direction['description']
        assert "Step change is very small" in caplog.text
    
    def test_minimal_step_zero_change(self, caplog):
        """Test MINIMAL-STEP with exactly zero change"""
        df = pd.DataFrame({
            'seconds': [-60, -50, -40, -30, -20, -10, 0, 10, 20, 30],
            'mode_power': [3500] * 10,
            'summary_wattage': [3500] * 10,
            'temp_hash_board_max': [65] * 10,
            'psu_temp_max': [45] * 10,
            'outage': [False] * 10
        })
        
        metrics = BasicMetrics(df, action_idx=6)
        start_power = metrics.calculate_start_power()
        target_power = metrics.calculate_target_power()
        
        with caplog.at_level('WARNING'):
            step_direction = metrics.calculate_step_direction(start_power, target_power)
        
        assert step_direction['direction'] == "MINIMAL-STEP"
        assert step_direction['delta'] == 0.0
    
    def test_boundary_exactly_50w_positive(self):
        """Test boundary case: exactly +50W should be MINIMAL-STEP"""
        df = pd.DataFrame({
            'seconds': [-60, -50, -40, -30, -20, -10, 0, 10, 20, 30],
            'mode_power': [3500] * 6 + [3550] * 4,
            'summary_wattage': [3500] * 6 + [3510, 3520, 3530, 3540],
            'temp_hash_board_max': [65] * 10,
            'psu_temp_max': [45] * 10,
            'outage': [False] * 10
        })
        
        metrics = BasicMetrics(df, action_idx=6)
        start_power = metrics.calculate_start_power()
        target_power = metrics.calculate_target_power()
        step_direction = metrics.calculate_step_direction(start_power, target_power)
        
        # delta = 3550 - 3500 = 50W, which is NOT > 50
        assert step_direction['direction'] == "MINIMAL-STEP"
        assert step_direction['delta'] == 50.0
    
    def test_boundary_just_over_50w(self):
        """Test boundary case: 51W should be UP-STEP"""
        df = pd.DataFrame({
            'seconds': [-60, -50, -40, -30, -20, -10, 0, 10, 20, 30],
            'mode_power': [3500] * 6 + [3551] * 4,
            'summary_wattage': [3500] * 6 + [3510, 3520, 3530, 3540],
            'temp_hash_board_max': [65] * 10,
            'psu_temp_max': [45] * 10,
            'outage': [False] * 10
        })
        
        metrics = BasicMetrics(df, action_idx=6)
        start_power = metrics.calculate_start_power()
        target_power = metrics.calculate_target_power()
        step_direction = metrics.calculate_step_direction(start_power, target_power)
        
        # delta = 3551 - 3500 = 51W, which is > 50
        assert step_direction['direction'] == "UP-STEP"
        assert step_direction['delta'] == 51.0
    
    def test_very_large_delta_warning(self, caplog):
        """Test that very large power changes generate info log"""
        df = pd.DataFrame({
            'seconds': [-60, -50, -40, -30, -20, -10, 0, 10, 20, 30],
            'mode_power': [500] * 6 + [5000] * 4,
            'summary_wattage': [500] * 6 + [1000, 2000, 3500, 4800],
            'temp_hash_board_max': [45] * 6 + [55, 65, 75, 85],
            'psu_temp_max': [30] * 6 + [35, 40, 45, 50],
            'outage': [False] * 10
        })
        
        metrics = BasicMetrics(df, action_idx=6)
        start_power = metrics.calculate_start_power()
        target_power = metrics.calculate_target_power()
        
        with caplog.at_level('INFO'):
            step_direction = metrics.calculate_step_direction(start_power, target_power)
        
        assert step_direction['direction'] == "UP-STEP"
        assert step_direction['delta'] > 2000
        assert "Very large power step detected" in caplog.text
    
    def test_missing_start_power_error(self):
        """Test error when start power is missing"""
        start_power = {'median': None, 'last_value': None, 'difference': None, 'note': None}
        target_power = {'before': 3500.0, 'after': 3600.0, 'change': 100.0}
        
        df = pd.DataFrame({'seconds': [0], 'mode_power': [3600], 'summary_wattage': [3590],
                          'temp_hash_board_max': [65], 'psu_temp_max': [45], 'outage': [False]})
        metrics = BasicMetrics(df, action_idx=0)
        
        with pytest.raises(ValueError, match="Cannot compute step direction"):
            metrics.calculate_step_direction(start_power, target_power)


class TestMetric4TemperatureRanges:
    """Tests for METRIC 4: Temperature Ranges analysis"""
    
    def test_normal_temperatures(self):
        """Test temperature ranges with complete valid data"""
        df = pd.DataFrame({
            'seconds': list(range(-60, 600, 10)),
            'mode_power': [3500] * 66,
            'summary_wattage': [3450] * 66,
            'temp_hash_board_max': list(range(50, 116)),  # 50 to 115°C
            'psu_temp_max': list(range(35, 101)),  # 35 to 100°C
            'outage': [False] * 66
        })
        
        metrics = BasicMetrics(df, action_idx=6)
        temp_ranges = metrics.calculate_temperature_ranges()
        
        # Validate structure
        assert 'psu' in temp_ranges
        assert 'board' in temp_ranges
        assert 'min' in temp_ranges['psu']
        assert 'max' in temp_ranges['psu']
        assert 'range' in temp_ranges['psu']
        
        # Validate PSU values
        assert temp_ranges['psu']['min'] == 35.0
        assert temp_ranges['psu']['max'] == 100.0
        assert temp_ranges['psu']['range'] == 65.0
        
        # Validate board values
        assert temp_ranges['board']['min'] == 50.0
        assert temp_ranges['board']['max'] == 115.0
        assert temp_ranges['board']['range'] == 65.0
    
    def test_all_psu_temps_nan(self, caplog):
        """Test when all PSU temperatures are NaN"""
        df = pd.DataFrame({
            'seconds': list(range(-60, 60, 10)),
            'mode_power': [3500] * 12,
            'summary_wattage': [3450] * 12,
            'temp_hash_board_max': [60, 62, 64, 66, 68, 70, 72, 74, 76, 78, 80, 82],
            'psu_temp_max': [np.nan] * 12,
            'outage': [False] * 12
        })
        
        metrics = BasicMetrics(df, action_idx=6)
        
        with caplog.at_level('WARNING'):
            temp_ranges = metrics.calculate_temperature_ranges()
        
        # PSU should all be None
        assert temp_ranges['psu']['min'] is None
        assert temp_ranges['psu']['max'] is None
        assert temp_ranges['psu']['range'] is None
        
        # Board should have values
        assert temp_ranges['board']['min'] == 60.0
        assert temp_ranges['board']['max'] == 82.0
        
        assert "All PSU temperature values are NaN" in caplog.text
    
    def test_all_board_temps_nan(self, caplog):
        """Test when all hash board temperatures are NaN"""
        df = pd.DataFrame({
            'seconds': list(range(-60, 60, 10)),
            'mode_power': [3500] * 12,
            'summary_wattage': [3450] * 12,
            'temp_hash_board_max': [np.nan] * 12,
            'psu_temp_max': [40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51],
            'outage': [False] * 12
        })
        
        metrics = BasicMetrics(df, action_idx=6)
        
        with caplog.at_level('WARNING'):
            temp_ranges = metrics.calculate_temperature_ranges()
        
        # Board should all be None
        assert temp_ranges['board']['min'] is None
        assert temp_ranges['board']['max'] is None
        assert temp_ranges['board']['range'] is None
        
        # PSU should have values
        assert temp_ranges['psu']['min'] == 40.0
        assert temp_ranges['psu']['max'] == 51.0
        
        assert "All hash board temperature values are NaN" in caplog.text
    
    def test_partial_nan_temperatures(self):
        """Test temperature ranges with some NaN values"""
        df = pd.DataFrame({
            'seconds': list(range(-60, 60, 10)),
            'mode_power': [3500] * 12,
            'summary_wattage': [3450] * 12,
            'temp_hash_board_max': [60, np.nan, 64, 66, np.nan, 70, 72, 74, np.nan, 78, 80, 82],
            'psu_temp_max': [40, 41, np.nan, 43, 44, np.nan, 46, 47, 48, np.nan, 50, 51],
            'outage': [False, True, False, False, True, False, False, False, True, False, False, False]
        })
        
        metrics = BasicMetrics(df, action_idx=6)
        temp_ranges = metrics.calculate_temperature_ranges()
        
        # Should compute from valid values only
        assert temp_ranges['psu']['min'] == 40.0
        assert temp_ranges['psu']['max'] == 51.0
        assert temp_ranges['board']['min'] == 60.0
        assert temp_ranges['board']['max'] == 82.0
    
    def test_temperature_outside_typical_range_warning(self, caplog):
        """Test warning for temperatures outside typical range"""
        df = pd.DataFrame({
            'seconds': list(range(-60, 60, 10)),
            'mode_power': [3500] * 12,
            'summary_wattage': [3450] * 12,
            'temp_hash_board_max': [-5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110],
            'psu_temp_max': [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120],
            'outage': [False] * 12
        })
        
        metrics = BasicMetrics(df, action_idx=6)
        
        with caplog.at_level('WARNING'):
            temp_ranges = metrics.calculate_temperature_ranges()
        
        # Should warn about -5°C (below 0) and 110°C, 120°C (above 100)
        assert "outside typical range" in caplog.text
        
        # But should still return the values
        assert temp_ranges['board']['min'] == -5.0
        assert temp_ranges['board']['max'] == 110.0
        assert temp_ranges['psu']['max'] == 120.0
    
    def test_constant_temperature(self):
        """Test with constant temperature (zero range)"""
        df = pd.DataFrame({
            'seconds': list(range(-60, 60, 10)),
            'mode_power': [3500] * 12,
            'summary_wattage': [3450] * 12,
            'temp_hash_board_max': [65.0] * 12,
            'psu_temp_max': [45.0] * 12,
            'outage': [False] * 12
        })
        
        metrics = BasicMetrics(df, action_idx=6)
        temp_ranges = metrics.calculate_temperature_ranges()
        
        # Range should be 0 for constant temperature
        assert temp_ranges['psu']['min'] == 45.0
        assert temp_ranges['psu']['max'] == 45.0
        assert temp_ranges['psu']['range'] == 0.0
        
        assert temp_ranges['board']['min'] == 65.0
        assert temp_ranges['board']['max'] == 65.0
        assert temp_ranges['board']['range'] == 0.0
    
    def test_temperature_ranges_validation(self):
        """Test that max >= min and range = max - min"""
        df = pd.DataFrame({
            'seconds': list(range(-60, 60, 10)),
            'mode_power': [3500] * 12,
            'summary_wattage': [3450] * 12,
            'temp_hash_board_max': [55, 58, 61, 64, 67, 70, 73, 76, 79, 82, 85, 88],
            'psu_temp_max': [38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49],
            'outage': [False] * 12
        })
        
        metrics = BasicMetrics(df, action_idx=6)
        temp_ranges = metrics.calculate_temperature_ranges()
        
        # Validate PSU
        assert temp_ranges['psu']['max'] >= temp_ranges['psu']['min']
        assert temp_ranges['psu']['range'] == pytest.approx(
            temp_ranges['psu']['max'] - temp_ranges['psu']['min']
        )
        
        # Validate board
        assert temp_ranges['board']['max'] >= temp_ranges['board']['min']
        assert temp_ranges['board']['range'] == pytest.approx(
            temp_ranges['board']['max'] - temp_ranges['board']['min']
        )

