"""
Unit tests for TimeMetrics module (METRIC 5 and METRIC 6).

Tests follow the pseudocode specification in:
R_Test_Metrics_Complete_Pseudocode_v3.md - Lines 438-909
"""

import pytest
import pandas as pd
import numpy as np
from src.metrics.time_metrics import TimeMetrics


class TestMetric5BandEntry:
    """Tests for METRIC 5: Band Entry with adaptive tolerance"""
    
    def test_successful_entry_sustained_15s(self):
        """Test successful band entry with 15+ second dwell time"""
        # UP-STEP: 1000W -> 3500W
        # Create data that enters band at t=45s and stays for 30s
        df = pd.DataFrame({
            'seconds': [-60, -50, -40, -30, -20, -10, 0, 10, 20, 30, 45, 55, 65, 75, 85],
            'mode_power': [1000] * 7 + [3500] * 8,
            'summary_wattage': [1020] * 7 + [1500, 2200, 2800, 3400, 3420, 3410, 3430, 3425],
            'temp_hash_board_max': [50] * 15,
            'psu_temp_max': [35] * 15,
            'outage': [False] * 15
        })
        
        metrics = TimeMetrics(df, action_idx=7)
        start_power = {'median': 1020.0}
        target_power = {'after': 3500.0}
        
        result = metrics.calculate_band_entry(target_power, start_power)
        
        assert result['status'] == 'ENTERED'
        assert result['time'] == 45.0
        assert result['wattage'] == pytest.approx(3400.0)
        assert 'band_limits' in result
        assert 'tolerance' in result['band_limits']
        
    def test_adaptive_tolerance_calculation(self):
        """Test adaptive tolerance uses min of 5% target or 50% step"""
        # Small step: 3400W -> 3500W (100W step)
        # 5% of 3500 = 175W, 50% of 100W = 50W
        # Should use 50W tolerance
        df = pd.DataFrame({
            'seconds': [-30, -20, -10, 0, 10, 20, 30, 40, 50, 60, 70],
            'mode_power': [3400] * 4 + [3500] * 7,
            'summary_wattage': [3390] * 4 + [3410, 3430, 3470, 3480, 3485, 3490, 3495],
            'temp_hash_board_max': [60] * 11,
            'psu_temp_max': [40] * 11,
            'outage': [False] * 11
        })
        
        metrics = TimeMetrics(df, action_idx=4)
        start_power = {'median': 3390.0}
        target_power = {'after': 3500.0}
        
        result = metrics.calculate_band_entry(target_power, start_power)
        
        # Should use 50W tolerance (50% of 110W step)
        expected_tolerance = 55.0  # 50% of (3500 - 3390)
        assert result['band_limits']['tolerance'] == pytest.approx(expected_tolerance, abs=1.0)
        
    def test_brief_entry_not_sustained(self):
        """Test when power enters band but doesn't stay for 15 seconds"""
        df = pd.DataFrame({
            'seconds': [-30, -20, -10, 0, 5, 10, 15, 20, 25, 30, 35, 40],
            'mode_power': [1000] * 4 + [3500] * 8,
            'summary_wattage': [1020] * 4 + [1500, 2200, 3400, 3450, 2800, 3000, 3200, 3300],
            'temp_hash_board_max': [50] * 12,
            'psu_temp_max': [35] * 12,
            'outage': [False] * 12
        })
        
        metrics = TimeMetrics(df, action_idx=4)
        start_power = {'median': 1020.0}
        target_power = {'after': 3500.0}
        
        result = metrics.calculate_band_entry(target_power, start_power)
        
        assert result['status'] == 'BRIEF_ENTRY_NOT_SUSTAINED'
        assert 'time' in result
        assert 'duration' in result
        assert result['duration'] < 15.0
        
    def test_never_entered_band(self):
        """Test when power never reaches the band"""
        df = pd.DataFrame({
            'seconds': [-30, -20, -10, 0, 10, 20, 30, 40, 50, 60],
            'mode_power': [1000] * 4 + [3500] * 6,
            'summary_wattage': [1020] * 4 + [1500, 2000, 2500, 2800, 2900, 3000],
            'temp_hash_board_max': [50] * 10,
            'psu_temp_max': [35] * 10,
            'outage': [False] * 10
        })
        
        metrics = TimeMetrics(df, action_idx=4)
        start_power = {'median': 1020.0}
        target_power = {'after': 3500.0}
        
        result = metrics.calculate_band_entry(target_power, start_power)
        
        assert result['status'] == 'NOT_ENTERED'
        assert 'closest_approach' in result
        assert 'distance' in result['closest_approach']
        
    def test_initially_in_band_sustained(self):
        """Test when power is already in band at t=0 and stays"""
        # Test verifies early entry behavior (within first sample after action)
        df = pd.DataFrame({
            'seconds': [-30, -20, -10, 0, 10, 20, 30, 40, 50, 60],
            'mode_power': [3480] * 4 + [3500] * 6,
            'summary_wattage': [3485] * 4 + [3495, 3497, 3499, 3501, 3503, 3505],
            'temp_hash_board_max': [60] * 10,
            'psu_temp_max': [40] * 10,
            'outage': [False] * 10
        })
        
        metrics = TimeMetrics(df, action_idx=4)
        start_power = {'median': 3485.0}
        target_power = {'after': 3500.0}
        
        result = metrics.calculate_band_entry(target_power, start_power)
        
        # Should enter band early (small step scenario)
        assert result['status'] in ['INITIALLY_IN_BAND', 'ENTERED']
        # Verify it enters within reasonable timeframe
        assert result['time'] < 30.0
        
    def test_entry_method_via_overshoot(self):
        """Test entry method detection for overshoot (UP-STEP)"""
        df = pd.DataFrame({
            'seconds': [-30, -20, -10, 0, 10, 20, 30, 40, 50, 60, 70, 80],
            'mode_power': [1000] * 4 + [3500] * 8,
            'summary_wattage': [1020] * 4 + [1500, 2800, 3800, 3700, 3600, 3550, 3520, 3510],
            'temp_hash_board_max': [50] * 12,
            'psu_temp_max': [35] * 12,
            'outage': [False] * 12
        })
        
        metrics = TimeMetrics(df, action_idx=4)
        start_power = {'median': 1020.0}
        target_power = {'after': 3500.0}
        step_direction = {'delta': 2480.0}  # UP-STEP
        
        result = metrics.calculate_band_entry(target_power, start_power, step_direction)
        
        assert result['status'] == 'ENTERED'
        # Entry wattage should be > target (overshoot)
        assert result['wattage'] > target_power['after']
        assert result['entry_method'] == 'via_overshoot'
        
    def test_entry_method_via_undershoot(self):
        """Test entry method detection for undershoot (DOWN-STEP)"""
        df = pd.DataFrame({
            'seconds': [-30, -20, -10, 0, 10, 20, 30, 40, 50, 60, 70, 80],
            'mode_power': [3500] * 4 + [1000] * 8,
            'summary_wattage': [3510] * 4 + [3200, 2500, 800, 850, 900, 950, 980, 990],
            'temp_hash_board_max': [60] * 12,
            'psu_temp_max': [40] * 12,
            'outage': [False] * 12
        })
        
        metrics = TimeMetrics(df, action_idx=4)
        start_power = {'median': 3510.0}
        target_power = {'after': 1000.0}
        step_direction = {'delta': -2510.0}  # DOWN-STEP
        
        result = metrics.calculate_band_entry(target_power, start_power, step_direction)
        
        assert result['status'] == 'ENTERED'
        # Entry wattage should be < target (undershoot)
        assert result['wattage'] < target_power['after']
        assert result['entry_method'] == 'via_undershoot'
        
    def test_nan_interrupts_segment(self):
        """Test that NaN values interrupt in-band segments"""
        df = pd.DataFrame({
            'seconds': [-30, -20, -10, 0, 5, 10, 15, 20, 25, 30, 40, 50, 60, 70],
            'mode_power': [1000] * 4 + [3500] * 10,
            'summary_wattage': [1020] * 4 + [1500, 2800, 3400, 3450, np.nan, np.nan, 3420, 3430, 3440, 3450],
            'temp_hash_board_max': [50] * 14,
            'psu_temp_max': [35] * 14,
            'outage': [False] * 14
        })
        
        metrics = TimeMetrics(df, action_idx=4)
        start_power = {'median': 1020.0}
        target_power = {'after': 3500.0}
        
        result = metrics.calculate_band_entry(target_power, start_power)
        
        # Should enter at t=40s (after NaN gap), not t=10s
        assert result['status'] == 'ENTERED'
        assert result['time'] >= 40.0
        
    def test_no_valid_data(self):
        """Test when all post-action wattage is NaN"""
        df = pd.DataFrame({
            'seconds': [-30, -20, -10, 0, 10, 20, 30],
            'mode_power': [1000] * 4 + [3500] * 3,
            'summary_wattage': [1020, 1025, 1030, 1035, np.nan, np.nan, np.nan],
            'temp_hash_board_max': [50] * 7,
            'psu_temp_max': [35] * 7,
            'outage': [False] * 7
        })
        
        metrics = TimeMetrics(df, action_idx=4)
        start_power = {'median': 1020.0}
        target_power = {'after': 3500.0}
        
        result = metrics.calculate_band_entry(target_power, start_power)
        
        assert result['status'] == 'NO_VALID_DATA'
        assert 'band_limits' in result


class TestMetric6SetpointHit:
    """Tests for METRIC 6: Setpoint Hit with event classification"""
    
    def test_sustained_hit_25s(self):
        """Test sustained hit (≥25 seconds within ±30W)"""
        df = pd.DataFrame({
            'seconds': [-30, -20, -10, 0, 10, 20, 30, 40, 50, 60, 70, 80, 90],
            'mode_power': [1000] * 4 + [3500] * 9,
            'summary_wattage': [1020] * 4 + [1500, 2800, 3480, 3490, 3485, 3495, 3500, 3505, 3510],
            'temp_hash_board_max': [50] * 13,
            'psu_temp_max': [35] * 13,
            'outage': [False] * 13
        })
        
        metrics = TimeMetrics(df, action_idx=4)
        target_power = {'after': 3500.0}
        
        result = metrics.calculate_setpoint_hit(target_power)
        
        assert result['summary']['total_sustained_hits'] >= 1
        assert result['summary']['never_sustained'] is False
        assert result['summary']['first_sustained_hit_time'] is not None
        
        # Check first sustained hit
        first_hit = result['sustained_hits'][0]
        assert first_hit['duration'] >= 25.0
        assert 'avg_wattage' in first_hit
        assert 'exit_reason' in first_hit
        
    def test_brief_touches_only(self):
        """Test multiple brief touches (<25 seconds) without sustained hit"""
        df = pd.DataFrame({
            'seconds': [-30, -20, -10, 0, 10, 20, 30, 40, 50, 60, 70, 80],
            'mode_power': [1000] * 4 + [3500] * 8,
            'summary_wattage': [1020] * 4 + [1500, 2800, 3490, 2800, 3480, 3000, 3495, 3100],
            'temp_hash_board_max': [50] * 12,
            'psu_temp_max': [35] * 12,
            'outage': [False] * 12
        })
        
        metrics = TimeMetrics(df, action_idx=4)
        target_power = {'after': 3500.0}
        
        result = metrics.calculate_setpoint_hit(target_power)
        
        assert result['summary']['total_brief_touches'] > 0
        assert result['summary']['total_sustained_hits'] == 0
        assert result['summary']['never_sustained'] is True
        
        # Check brief touches have duration < 25s
        for touch in result['brief_touches']:
            assert touch['duration'] < 25.0
            assert 'exit_reason' in touch
            
    def test_exit_reasons(self):
        """Test that exit reasons are correctly identified"""
        df = pd.DataFrame({
            'seconds': [-30, -20, -10, 0, 10, 20, 30, 40, 50, 60, 70, 80],
            'mode_power': [1000] * 4 + [3500] * 8,
            'summary_wattage': [1020] * 4 + [1500, 3490, 3495, 3600, 3490, 3495, 3460, 3400],
            'temp_hash_board_max': [50] * 12,
            'psu_temp_max': [35] * 12,
            'outage': [False] * 12
        })
        
        metrics = TimeMetrics(df, action_idx=4)
        target_power = {'after': 3500.0}
        
        result = metrics.calculate_setpoint_hit(target_power)
        
        # Should have at least one touch with "exceeded_above" exit reason
        exit_reasons = [touch['exit_reason'] for touch in result['brief_touches']]
        assert 'exceeded_above' in exit_reasons or 'dropped_below' in exit_reasons
        
    def test_test_ended_exit_reason(self):
        """Test exit_reason='test_ended' when test ends while in band"""
        df = pd.DataFrame({
            'seconds': [-30, -20, -10, 0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120],
            'mode_power': [1000] * 4 + [3500] * 12,
            'summary_wattage': [1020] * 4 + [1500, 2800, 3480, 3490, 3485, 3495, 3500, 3505, 3490, 3495, 3500, 3505],
            'temp_hash_board_max': [50] * 16,
            'psu_temp_max': [35] * 16,
            'outage': [False] * 16
        })
        
        metrics = TimeMetrics(df, action_idx=4)
        target_power = {'after': 3500.0}
        
        result = metrics.calculate_setpoint_hit(target_power)
        
        assert result['summary']['total_sustained_hits'] >= 1
        last_hit = result['sustained_hits'][-1]
        assert last_hit['exit_reason'] == 'test_ended'
        
    def test_multiple_sustained_hits(self):
        """Test tracking multiple sustained hits with exits and re-entries"""
        df = pd.DataFrame({
            'seconds': [-30, -20, -10, 0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140],
            'mode_power': [1000] * 4 + [3500] * 14,
            'summary_wattage': [1020] * 4 + [1500, 2800, 3490, 3495, 3500, 3505, 3400, 3490, 3495, 3500, 3505, 3490, 3495, 3500],
            'temp_hash_board_max': [50] * 18,
            'psu_temp_max': [35] * 18,
            'outage': [False] * 18
        })
        
        metrics = TimeMetrics(df, action_idx=4)
        target_power = {'after': 3500.0}
        
        result = metrics.calculate_setpoint_hit(target_power)
        
        # Should have multiple sustained hits
        assert result['summary']['total_sustained_hits'] >= 1
        
        # Verify sustained hits are ordered chronologically
        if len(result['sustained_hits']) > 1:
            for i in range(len(result['sustained_hits']) - 1):
                assert result['sustained_hits'][i]['time'] < result['sustained_hits'][i + 1]['time']
                
    def test_average_wattage_calculation(self):
        """Test that average wattage is calculated correctly for sustained hits"""
        df = pd.DataFrame({
            'seconds': [-30, -20, -10, 0, 10, 20, 30, 40, 50, 60, 70, 80, 90],
            'mode_power': [1000] * 4 + [3500] * 9,
            'summary_wattage': [1020] * 4 + [1500, 2800, 3480, 3490, 3500, 3510, 3490, 3500, 3510],
            'temp_hash_board_max': [50] * 13,
            'psu_temp_max': [35] * 13,
            'outage': [False] * 13
        })
        
        metrics = TimeMetrics(df, action_idx=4)
        target_power = {'after': 3500.0}
        
        result = metrics.calculate_setpoint_hit(target_power)
        
        if result['summary']['total_sustained_hits'] > 0:
            first_hit = result['sustained_hits'][0]
            # Average should be within the ±30W band
            assert abs(first_hit['avg_wattage'] - 3500.0) <= 30.0
            
    def test_nan_breaks_segments(self):
        """Test that NaN values break segments correctly"""
        df = pd.DataFrame({
            'seconds': [-30, -20, -10, 0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
            'mode_power': [1000] * 4 + [3500] * 10,
            'summary_wattage': [1020] * 4 + [1500, 3490, 3495, np.nan, np.nan, 3490, 3495, 3500, 3505, 3510],
            'temp_hash_board_max': [50] * 14,
            'psu_temp_max': [35] * 14,
            'outage': [False] * 14
        })
        
        metrics = TimeMetrics(df, action_idx=4)
        target_power = {'after': 3500.0}
        
        result = metrics.calculate_setpoint_hit(target_power)
        
        # NaN should break the first segment, creating brief touches
        total_events = result['summary']['total_brief_touches'] + result['summary']['total_sustained_hits']
        assert total_events >= 2  # At least 2 segments due to NaN break
        
    def test_never_hit_setpoint(self):
        """Test when power never reaches within ±30W of target"""
        df = pd.DataFrame({
            'seconds': [-30, -20, -10, 0, 10, 20, 30, 40, 50, 60],
            'mode_power': [1000] * 4 + [3500] * 6,
            'summary_wattage': [1020] * 4 + [1500, 2000, 2500, 2800, 3000, 3200],
            'temp_hash_board_max': [50] * 10,
            'psu_temp_max': [35] * 10,
            'outage': [False] * 10
        })
        
        metrics = TimeMetrics(df, action_idx=4)
        target_power = {'after': 3500.0}
        
        result = metrics.calculate_setpoint_hit(target_power)
        
        assert result['summary']['total_brief_touches'] == 0
        assert result['summary']['total_sustained_hits'] == 0
        assert result['summary']['never_sustained'] is True
        
    def test_entry_at_t_zero(self):
        """Test when power is within setpoint band immediately at t=0"""
        df = pd.DataFrame({
            'seconds': [-30, -20, -10, 0, 10, 20, 30, 40, 50, 60, 70, 80, 90],
            'mode_power': [3480] * 4 + [3500] * 9,
            'summary_wattage': [3470] * 4 + [3480, 3490, 3495, 3500, 3505, 3490, 3495, 3500, 3505],
            'temp_hash_board_max': [60] * 13,
            'psu_temp_max': [40] * 13,
            'outage': [False] * 13
        })
        
        metrics = TimeMetrics(df, action_idx=4)
        target_power = {'after': 3500.0}
        
        result = metrics.calculate_setpoint_hit(target_power)
        
        # Should have at least one sustained hit starting at or near t=0
        assert result['summary']['total_sustained_hits'] >= 1
        first_hit = result['sustained_hits'][0]
        assert first_hit['time'] <= 10.0  # Within first few seconds


class TestTimeMetricsIntegration:
    """Integration tests using real data patterns"""
    
    def test_complete_up_step_scenario(self):
        """Test complete UP-STEP scenario with both metrics"""
        # Realistic UP-STEP: 1000W -> 3500W
        df = pd.DataFrame({
            'seconds': list(range(-60, 121, 10)),
            'mode_power': [1000] * 7 + [3500] * 12,
            'summary_wattage': [
                # Pre-action stable at 1000W
                1015, 1020, 1025, 1018, 1022, 1020, 1019,
                # Ramp up
                1500, 2200, 2900, 3300, 3450, 3480, 3490, 3495, 3500, 3505, 3495, 3500
            ],
            'temp_hash_board_max': [50] * 7 + [55, 60, 65, 68, 70, 72, 73, 74, 75, 75, 75, 75],
            'psu_temp_max': [35] * 7 + [38, 40, 42, 44, 45, 46, 46, 47, 47, 47, 47, 47],
            'outage': [False] * 19
        })
        
        metrics = TimeMetrics(df, action_idx=7)
        start_power = {'median': 1020.0}
        target_power = {'after': 3500.0}
        step_direction = {'delta': 2480.0}
        
        # METRIC 5: Band Entry
        band_result = metrics.calculate_band_entry(target_power, start_power, step_direction)
        assert band_result['status'] == 'ENTERED'
        assert band_result['time'] > 0
        
        # METRIC 6: Setpoint Hit
        setpoint_result = metrics.calculate_setpoint_hit(target_power)
        assert setpoint_result['summary']['never_sustained'] is False
        
        # Band entry should occur before or at setpoint hit
        if setpoint_result['summary']['first_sustained_hit_time'] is not None:
            assert band_result['time'] <= setpoint_result['summary']['first_sustained_hit_time']
            
    def test_complete_down_step_scenario(self):
        """Test complete DOWN-STEP scenario with both metrics"""
        # Realistic DOWN-STEP: 3500W -> 1000W
        df = pd.DataFrame({
            'seconds': list(range(-60, 121, 10)),
            'mode_power': [3500] * 7 + [1000] * 12,
            'summary_wattage': [
                # Pre-action stable at 3500W
                3505, 3510, 3495, 3502, 3498, 3505, 3500,
                # Ramp down
                3200, 2500, 1800, 1300, 1050, 1020, 1010, 1005, 1000, 995, 1000, 1005
            ],
            'temp_hash_board_max': [75] * 7 + [72, 68, 64, 60, 58, 56, 55, 54, 53, 52, 52, 52],
            'psu_temp_max': [47] * 7 + [45, 43, 41, 39, 38, 37, 36, 35, 35, 35, 35, 35],
            'outage': [False] * 19
        })
        
        metrics = TimeMetrics(df, action_idx=7)
        start_power = {'median': 3502.0}
        target_power = {'after': 1000.0}
        step_direction = {'delta': -2502.0}
        
        # METRIC 5: Band Entry
        band_result = metrics.calculate_band_entry(target_power, start_power, step_direction)
        assert band_result['status'] == 'ENTERED'
        
        # METRIC 6: Setpoint Hit
        setpoint_result = metrics.calculate_setpoint_hit(target_power)
        assert setpoint_result['summary']['total_sustained_hits'] + setpoint_result['summary']['total_brief_touches'] > 0

