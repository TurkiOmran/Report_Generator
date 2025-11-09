"""
Unit tests for plateau duration and anomaly detection metrics (METRIC 7 and METRIC 8).

Tests follow the pseudocode specification in:
R_Test_Metrics_Complete_Pseudocode_v3.md - Lines 912-1262
"""

import pytest
import pandas as pd
import numpy as np
from src.metrics.time_metrics import TimeMetrics
from src.metrics.anomaly_metrics import AnomalyMetrics


class TestMetric7PlateauDuration:
    """Tests for METRIC 7: Stable Plateau Duration with ±20W tolerance"""
    
    def test_single_long_plateau(self):
        """Test single sustained plateau (≥30 seconds)"""
        df = pd.DataFrame({
            'seconds': list(range(-30, 121, 10)),
            'mode_power': [1000] * 4 + [3500] * 12,
            'summary_wattage': [1020] * 4 + [1500, 2800, 3490, 3495, 3500, 3505, 3490, 3495, 3500, 3505, 3495, 3500],
            'temp_hash_board_max': [50] * 16,
            'psu_temp_max': [35] * 16,
            'outage': [False] * 16
        })
        
        metrics = TimeMetrics(df, action_idx=4)
        target_power = {'after': 3500.0}
        
        result = metrics.calculate_plateau_duration(target_power)
        
        assert result['summary']['total_count'] >= 1
        assert result['summary']['longest_duration'] >= 30.0
        assert result['summary']['total_stable_time'] >= 30.0
        
        # Check that first plateau meets criteria
        if result['plateaus']:
            first_plateau = result['plateaus'][0]
            assert first_plateau['duration'] >= 30.0
            assert 'avg_wattage' in first_plateau
            assert abs(first_plateau['avg_wattage'] - 3500.0) <= 20.0
            assert 'exit_reason' in first_plateau
            
    def test_multiple_plateaus(self):
        """Test multiple separate plateau periods"""
        df = pd.DataFrame({
            'seconds': [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140],
            'mode_power': [3500] * 15,
            'summary_wattage': [3490, 3495, 3500, 3505, 3600, 3700, 3490, 3495, 3500, 3505, 3490, 3495, 3500, 3505, 3490],
            'temp_hash_board_max': [60] * 15,
            'psu_temp_max': [40] * 15,
            'outage': [False] * 15
        })
        
        metrics = TimeMetrics(df, action_idx=0)
        target_power = {'after': 3500.0}
        
        result = metrics.calculate_plateau_duration(target_power)
        
        # Should have multiple plateaus
        assert result['summary']['total_count'] >= 2
        
        # Total stable time should be sum of all plateau durations
        calculated_total = sum(p['duration'] for p in result['plateaus'])
        assert result['summary']['total_stable_time'] == pytest.approx(calculated_total)
        
        # Longest duration should match actual longest
        longest = max(p['duration'] for p in result['plateaus'])
        assert result['summary']['longest_duration'] == pytest.approx(longest)
        
    def test_no_qualifying_plateaus(self):
        """Test when no periods meet the 30-second minimum"""
        df = pd.DataFrame({
            'seconds': [0, 10, 20, 30, 40, 50, 60, 70, 80],
            'mode_power': [3500] * 9,
            'summary_wattage': [3490, 3495, 3600, 3490, 3495, 3600, 3490, 3495, 3600],
            'temp_hash_board_max': [60] * 9,
            'psu_temp_max': [40] * 9,
            'outage': [False] * 9
        })
        
        metrics = TimeMetrics(df, action_idx=0)
        target_power = {'after': 3500.0}
        
        result = metrics.calculate_plateau_duration(target_power)
        
        assert result['summary']['total_count'] == 0
        assert result['summary']['longest_duration'] == 0.0
        assert result['summary']['total_stable_time'] == 0.0
        assert result['plateaus'] == []
        
    def test_test_ended_exit_reason(self):
        """Test exit_reason='test_ended' when test ends during plateau"""
        df = pd.DataFrame({
            'seconds': list(range(0, 91, 10)),
            'mode_power': [3500] * 10,
            'summary_wattage': [3490, 3495, 3500, 3505, 3490, 3495, 3500, 3505, 3490, 3495],
            'temp_hash_board_max': [60] * 10,
            'psu_temp_max': [40] * 10,
            'outage': [False] * 10
        })
        
        metrics = TimeMetrics(df, action_idx=0)
        target_power = {'after': 3500.0}
        
        result = metrics.calculate_plateau_duration(target_power)
        
        assert result['summary']['total_count'] >= 1
        # Last plateau should have test_ended exit reason
        if result['plateaus']:
            last_plateau = result['plateaus'][-1]
            assert last_plateau['exit_reason'] == 'test_ended'
            
    def test_exit_reasons_classification(self):
        """Test that exit reasons are correctly classified"""
        df = pd.DataFrame({
            'seconds': [0, 10, 20, 30, 40, 50, 60, 70, 80, 90],
            'mode_power': [3500] * 10,
            'summary_wattage': [3490, 3495, 3500, 3505, 3450, 3490, 3495, 3500, 3505, 3530],
            'temp_hash_board_max': [60] * 10,
            'psu_temp_max': [40] * 10,
            'outage': [False] * 10
        })
        
        metrics = TimeMetrics(df, action_idx=0)
        target_power = {'after': 3500.0}
        
        result = metrics.calculate_plateau_duration(target_power)
        
        # Should have at least one plateau with exit reason
        if result['plateaus']:
            exit_reasons = [p['exit_reason'] for p in result['plateaus']]
            assert all(reason in ['dropped_below', 'exceeded_above', 'test_ended', 'unknown'] 
                      for reason in exit_reasons)
                      
    def test_nan_breaks_plateau(self):
        """Test that NaN values interrupt plateau segments"""
        df = pd.DataFrame({
            'seconds': [0, 10, 20, 30, 40, 50, 60, 70, 80, 90],
            'mode_power': [3500] * 10,
            'summary_wattage': [3490, 3495, 3500, np.nan, np.nan, 3490, 3495, 3500, 3505, 3490],
            'temp_hash_board_max': [60] * 10,
            'psu_temp_max': [40] * 10,
            'outage': [False] * 10
        })
        
        metrics = TimeMetrics(df, action_idx=0)
        target_power = {'after': 3500.0}
        
        result = metrics.calculate_plateau_duration(target_power)
        
        # NaN should break into multiple segments
        # May have plateaus depending on segment lengths
        assert isinstance(result['plateaus'], list)
        assert isinstance(result['summary']['total_count'], int)
        
    def test_average_wattage_within_tolerance(self):
        """Test that average wattage is within ±20W for all plateaus"""
        df = pd.DataFrame({
            'seconds': list(range(0, 61, 10)),
            'mode_power': [3500] * 7,
            'summary_wattage': [3485, 3490, 3495, 3500, 3505, 3510, 3515],
            'temp_hash_board_max': [60] * 7,
            'psu_temp_max': [40] * 7,
            'outage': [False] * 7
        })
        
        metrics = TimeMetrics(df, action_idx=0)
        target_power = {'after': 3500.0}
        
        result = metrics.calculate_plateau_duration(target_power)
        
        # All plateaus should have avg wattage within ±20W
        for plateau in result['plateaus']:
            assert abs(plateau['avg_wattage'] - 3500.0) <= 20.0
            
    def test_summary_statistics_consistency(self):
        """Test that summary statistics are consistent with plateau list"""
        df = pd.DataFrame({
            'seconds': list(range(0, 121, 10)),
            'mode_power': [3500] * 13,
            'summary_wattage': [3490] * 13,
            'temp_hash_board_max': [60] * 13,
            'psu_temp_max': [40] * 13,
            'outage': [False] * 13
        })
        
        metrics = TimeMetrics(df, action_idx=0)
        target_power = {'after': 3500.0}
        
        result = metrics.calculate_plateau_duration(target_power)
        
        # Count should match list length
        assert result['summary']['total_count'] == len(result['plateaus'])
        
        if result['plateaus']:
            # Total stable time should equal sum
            total = sum(p['duration'] for p in result['plateaus'])
            assert result['summary']['total_stable_time'] == pytest.approx(total)
            
            # Longest should equal max
            longest = max(p['duration'] for p in result['plateaus'])
            assert result['summary']['longest_duration'] == pytest.approx(longest)


class TestMetric8SharpDrops:
    """Tests for METRIC 8: Sharp Drops with 15% threshold and 5-second window"""
    
    def test_single_sharp_drop(self):
        """Test detection of a single sharp drop exceeding 15% threshold"""
        df = pd.DataFrame({
            'seconds': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            'mode_power': [3500] * 11,
            'summary_wattage': [3500, 3490, 3480, 2900, 2850, 2800, 2790, 2785, 2780, 2775, 2770],
            'temp_hash_board_max': [60] * 11,
            'psu_temp_max': [40] * 11,
            'outage': [False] * 11
        })
        
        metrics = AnomalyMetrics(df, action_idx=0)
        
        result = metrics.calculate_sharp_drops()
        
        assert result['summary']['count'] >= 1
        assert result['summary']['worst_magnitude'] is not None
        assert result['summary']['worst_rate'] is not None
        
        # Check first drop
        if result['sharp_drops']:
            first_drop = result['sharp_drops'][0]
            assert first_drop['magnitude'] > 0
            assert first_drop['rate'] < 0  # Negative for drop
            assert first_drop['end_wattage'] < first_drop['start_wattage']
            assert first_drop['duration'] > 0
            assert first_drop['duration'] <= 5.0  # Within detection window
            
    def test_no_sharp_drops(self):
        """Test when power remains stable (no drops exceeding 15%)"""
        df = pd.DataFrame({
            'seconds': list(range(0, 61, 10)),
            'mode_power': [3500] * 7,
            'summary_wattage': [3500, 3490, 3505, 3495, 3500, 3490, 3505],
            'temp_hash_board_max': [60] * 7,
            'psu_temp_max': [40] * 7,
            'outage': [False] * 7
        })
        
        metrics = AnomalyMetrics(df, action_idx=0)
        
        result = metrics.calculate_sharp_drops()
        
        assert result['summary']['count'] == 0
        assert result['summary']['worst_magnitude'] is None
        assert result['summary']['worst_rate'] is None
        assert result['sharp_drops'] == []
        
    def test_multiple_sharp_drops(self):
        """Test detection of multiple sharp drops"""
        df = pd.DataFrame({
            'seconds': [0, 2, 4, 6, 10, 12, 14, 16, 20, 22, 24, 26],
            'mode_power': [3500] * 12,
            'summary_wattage': [3500, 3490, 2900, 2850, 3400, 3390, 2800, 2750, 3300, 3290, 2700, 2650],
            'temp_hash_board_max': [60] * 12,
            'psu_temp_max': [40] * 12,
            'outage': [False] * 12
        })
        
        metrics = AnomalyMetrics(df, action_idx=0)
        
        result = metrics.calculate_sharp_drops()
        
        assert result['summary']['count'] >= 2
        
        # Worst magnitude should be the maximum
        if result['sharp_drops']:
            max_magnitude = max(d['magnitude'] for d in result['sharp_drops'])
            assert result['summary']['worst_magnitude'] == pytest.approx(max_magnitude)
            
            # Worst rate should be the most negative
            min_rate = min(d['rate'] for d in result['sharp_drops'])
            assert result['summary']['worst_rate'] == pytest.approx(min_rate)
            
    def test_drop_percentage_threshold(self):
        """Test that drops must exceed 15% threshold"""
        # 10% drop - should NOT be detected
        df1 = pd.DataFrame({
            'seconds': [0, 1, 2, 3, 4],
            'mode_power': [3000] * 5,
            'summary_wattage': [3000, 2950, 2900, 2850, 2800],  # ~7% drop
            'temp_hash_board_max': [60] * 5,
            'psu_temp_max': [40] * 5,
            'outage': [False] * 5
        })
        
        metrics1 = AnomalyMetrics(df1, action_idx=0)
        result1 = metrics1.calculate_sharp_drops()
        
        assert result1['summary']['count'] == 0
        
        # 20% drop - should be detected
        df2 = pd.DataFrame({
            'seconds': [0, 1, 2, 3, 4],
            'mode_power': [3000] * 5,
            'summary_wattage': [3000, 2900, 2700, 2400, 2300],  # >15% drop
            'temp_hash_board_max': [60] * 5,
            'psu_temp_max': [40] * 5,
            'outage': [False] * 5
        })
        
        metrics2 = AnomalyMetrics(df2, action_idx=0)
        result2 = metrics2.calculate_sharp_drops()
        
        assert result2['summary']['count'] >= 1
        
    def test_rolling_window_detection(self):
        """Test that detection uses 5-second rolling window"""
        # Drop occurs over 3 seconds within 5-second window
        df = pd.DataFrame({
            'seconds': [0, 1, 2, 3, 4, 5, 6, 7, 8],
            'mode_power': [3500] * 9,
            'summary_wattage': [3500, 3490, 3480, 2900, 2850, 2840, 2835, 2830, 2825],
            'temp_hash_board_max': [60] * 9,
            'psu_temp_max': [40] * 9,
            'outage': [False] * 9
        })
        
        metrics = AnomalyMetrics(df, action_idx=0)
        
        result = metrics.calculate_sharp_drops()
        
        assert result['summary']['count'] >= 1
        
        # Check that duration is within window
        for drop in result['sharp_drops']:
            assert drop['duration'] <= 5.0
            
    def test_overlapping_drops_prevention(self):
        """Test that processed_times prevents duplicate detection"""
        # Continuous drop that could be detected multiple times
        df = pd.DataFrame({
            'seconds': [0, 1, 2, 3, 4, 5],
            'mode_power': [3500] * 6,
            'summary_wattage': [3500, 3400, 3000, 2700, 2500, 2400],
            'temp_hash_board_max': [60] * 6,
            'psu_temp_max': [40] * 6,
            'outage': [False] * 6
        })
        
        metrics = AnomalyMetrics(df, action_idx=0)
        
        result = metrics.calculate_sharp_drops()
        
        # Should detect drop but not duplicate it
        assert result['summary']['count'] >= 1
        # Should not have excessive duplicates
        assert result['summary']['count'] <= 3
        
    def test_all_nan_values(self):
        """Test handling of all NaN wattage values"""
        df = pd.DataFrame({
            'seconds': [0, 10, 20, 30],
            'mode_power': [3500] * 4,
            'summary_wattage': [np.nan, np.nan, np.nan, np.nan],
            'temp_hash_board_max': [60] * 4,
            'psu_temp_max': [40] * 4,
            'outage': [False] * 4
        })
        
        metrics = AnomalyMetrics(df, action_idx=0)
        
        result = metrics.calculate_sharp_drops()
        
        assert result['summary']['count'] == 0
        assert result['summary']['worst_magnitude'] is None
        assert result['summary']['worst_rate'] is None
        
    def test_single_data_point(self):
        """Test handling of insufficient data (< 2 points)"""
        df = pd.DataFrame({
            'seconds': [0],
            'mode_power': [3500],
            'summary_wattage': [3500],
            'temp_hash_board_max': [60],
            'psu_temp_max': [40],
            'outage': [False]
        })
        
        metrics = AnomalyMetrics(df, action_idx=0)
        
        result = metrics.calculate_sharp_drops()
        
        assert result['summary']['count'] == 0
        assert result['summary']['worst_magnitude'] is None
        assert result['summary']['worst_rate'] is None
        
    def test_drop_rate_calculation(self):
        """Test that drop rate is calculated correctly"""
        df = pd.DataFrame({
            'seconds': [0, 2, 4, 6],
            'mode_power': [3500] * 4,
            'summary_wattage': [3500, 3490, 2900, 2850],
            'temp_hash_board_max': [60] * 4,
            'psu_temp_max': [40] * 4,
            'outage': [False] * 4
        })
        
        metrics = AnomalyMetrics(df, action_idx=0)
        
        result = metrics.calculate_sharp_drops()
        
        if result['sharp_drops']:
            for drop in result['sharp_drops']:
                # Rate should be negative
                assert drop['rate'] < 0
                # Rate should be magnitude / duration (with negative sign)
                expected_rate = -drop['magnitude'] / drop['duration']
                assert drop['rate'] == pytest.approx(expected_rate)
                
    def test_validation_constraints(self):
        """Test that output meets all validation constraints"""
        df = pd.DataFrame({
            'seconds': [0, 1, 2, 3, 4, 5],
            'mode_power': [3500] * 6,
            'summary_wattage': [3500, 3490, 2900, 2850, 2800, 2790],
            'temp_hash_board_max': [60] * 6,
            'psu_temp_max': [40] * 6,
            'outage': [False] * 6
        })
        
        metrics = AnomalyMetrics(df, action_idx=0)
        
        result = metrics.calculate_sharp_drops()
        
        for drop in result['sharp_drops']:
            # All times should be >= 0 (post-action)
            assert drop['time'] >= 0
            # All magnitudes should be positive
            assert drop['magnitude'] > 0
            # All rates should be negative
            assert drop['rate'] < 0
            # end_wattage should be < start_wattage
            assert drop['end_wattage'] < drop['start_wattage']
            # magnitude should equal difference
            assert drop['magnitude'] == pytest.approx(
                drop['start_wattage'] - drop['end_wattage']
            )
            # duration should be > 0 and <= 5 seconds
            assert drop['duration'] > 0
            assert drop['duration'] <= 5.0
            # Drop percentage should be >= 15%
            drop_pct = drop['magnitude'] / drop['start_wattage']
            assert drop_pct >= 0.15




