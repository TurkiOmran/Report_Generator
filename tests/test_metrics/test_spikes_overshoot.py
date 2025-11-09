"""
Unit tests for METRIC 9 (Spikes) and METRIC 10 (Overshoot/Undershoot).

Tests follow the pseudocode specification in:
R_Test_Metrics_Complete_Pseudocode_v3.md - Lines 1265-1651
"""

import pytest
import pandas as pd
import numpy as np
from src.metrics.anomaly_metrics import AnomalyMetrics


class TestMetric9Spikes:
    """Tests for METRIC 9: Spikes with 15% threshold and 5-second window"""
    
    def test_single_spike_detection(self):
        """Test detection of a single spike exceeding 15% threshold"""
        df = pd.DataFrame({
            'seconds': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            'mode_power': [3500] * 11,
            'summary_wattage': [3200, 3210, 3220, 3750, 3760, 3770, 3780, 3775, 3770, 3765, 3760],
            'temp_hash_board_max': [60] * 11,
            'psu_temp_max': [40] * 11,
            'outage': [False] * 11
        })
        
        metrics = AnomalyMetrics(df, action_idx=0)
        
        result = metrics.calculate_spikes()
        
        assert result['summary']['count'] >= 1
        assert result['summary']['worst_magnitude'] is not None
        assert result['summary']['worst_rate'] is not None
        
        # Check first spike
        if result['spikes']:
            first_spike = result['spikes'][0]
            assert first_spike['magnitude'] > 0
            assert first_spike['rate'] > 0  # Positive for spike
            assert first_spike['end_wattage'] > first_spike['start_wattage']
            assert first_spike['duration'] > 0
            assert first_spike['duration'] <= 5.0  # Within detection window
            
    def test_no_spikes(self):
        """Test when power remains stable (no spikes exceeding 15%)"""
        df = pd.DataFrame({
            'seconds': list(range(0, 61, 10)),
            'mode_power': [3500] * 7,
            'summary_wattage': [3500, 3510, 3505, 3495, 3500, 3490, 3505],
            'temp_hash_board_max': [60] * 7,
            'psu_temp_max': [40] * 7,
            'outage': [False] * 7
        })
        
        metrics = AnomalyMetrics(df, action_idx=0)
        
        result = metrics.calculate_spikes()
        
        assert result['summary']['count'] == 0
        assert result['summary']['worst_magnitude'] is None
        assert result['summary']['worst_rate'] is None
        assert result['spikes'] == []
        
    def test_multiple_spikes(self):
        """Test detection of multiple spikes"""
        df = pd.DataFrame({
            'seconds': [0, 2, 4, 6, 10, 12, 14, 16, 20, 22, 24, 26],
            'mode_power': [3500] * 12,
            'summary_wattage': [3200, 3210, 3750, 3760, 3300, 3310, 3850, 3860, 3400, 3410, 3950, 3960],
            'temp_hash_board_max': [60] * 12,
            'psu_temp_max': [40] * 12,
            'outage': [False] * 12
        })
        
        metrics = AnomalyMetrics(df, action_idx=0)
        
        result = metrics.calculate_spikes()
        
        assert result['summary']['count'] >= 2
        
        # Worst magnitude should be the maximum
        if result['spikes']:
            max_magnitude = max(s['magnitude'] for s in result['spikes'])
            assert result['summary']['worst_magnitude'] == pytest.approx(max_magnitude)
            
            # Worst rate should be the most positive
            max_rate = max(s['rate'] for s in result['spikes'])
            assert result['summary']['worst_rate'] == pytest.approx(max_rate)
            
    def test_spike_percentage_threshold(self):
        """Test that spikes must exceed 15% threshold"""
        # 10% spike - should NOT be detected
        df1 = pd.DataFrame({
            'seconds': [0, 1, 2, 3, 4],
            'mode_power': [3000] * 5,
            'summary_wattage': [3000, 3050, 3100, 3150, 3200],  # ~7% spike
            'temp_hash_board_max': [60] * 5,
            'psu_temp_max': [40] * 5,
            'outage': [False] * 5
        })
        
        metrics1 = AnomalyMetrics(df1, action_idx=0)
        result1 = metrics1.calculate_spikes()
        
        assert result1['summary']['count'] == 0
        
        # 20% spike - should be detected
        df2 = pd.DataFrame({
            'seconds': [0, 1, 2, 3, 4],
            'mode_power': [3000] * 5,
            'summary_wattage': [3000, 3100, 3300, 3600, 3700],  # >15% spike
            'temp_hash_board_max': [60] * 5,
            'psu_temp_max': [40] * 5,
            'outage': [False] * 5
        })
        
        metrics2 = AnomalyMetrics(df2, action_idx=0)
        result2 = metrics2.calculate_spikes()
        
        assert result2['summary']['count'] >= 1
        
    def test_rolling_window_detection(self):
        """Test that detection uses 5-second rolling window"""
        # Spike occurs over 3 seconds within 5-second window
        df = pd.DataFrame({
            'seconds': [0, 1, 2, 3, 4, 5, 6, 7, 8],
            'mode_power': [3500] * 9,
            'summary_wattage': [3200, 3210, 3220, 3750, 3760, 3770, 3775, 3780, 3785],
            'temp_hash_board_max': [60] * 9,
            'psu_temp_max': [40] * 9,
            'outage': [False] * 9
        })
        
        metrics = AnomalyMetrics(df, action_idx=0)
        
        result = metrics.calculate_spikes()
        
        assert result['summary']['count'] >= 1
        
        # Check that duration is within window
        for spike in result['spikes']:
            assert spike['duration'] <= 5.0
            
    def test_overlapping_spikes_prevention(self):
        """Test that processed_times prevents duplicate detection"""
        # Continuous spike that could be detected multiple times
        df = pd.DataFrame({
            'seconds': [0, 1, 2, 3, 4, 5],
            'mode_power': [3500] * 6,
            'summary_wattage': [3000, 3200, 3500, 3800, 4000, 4100],
            'temp_hash_board_max': [60] * 6,
            'psu_temp_max': [40] * 6,
            'outage': [False] * 6
        })
        
        metrics = AnomalyMetrics(df, action_idx=0)
        
        result = metrics.calculate_spikes()
        
        # Should detect spike but not duplicate it
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
        
        result = metrics.calculate_spikes()
        
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
        
        result = metrics.calculate_spikes()
        
        assert result['summary']['count'] == 0
        assert result['summary']['worst_magnitude'] is None
        assert result['summary']['worst_rate'] is None
        
    def test_spike_rate_calculation(self):
        """Test that spike rate is calculated correctly"""
        df = pd.DataFrame({
            'seconds': [0, 2, 4, 6],
            'mode_power': [3500] * 4,
            'summary_wattage': [3200, 3210, 3750, 3760],
            'temp_hash_board_max': [60] * 4,
            'psu_temp_max': [40] * 4,
            'outage': [False] * 4
        })
        
        metrics = AnomalyMetrics(df, action_idx=0)
        
        result = metrics.calculate_spikes()
        
        if result['spikes']:
            for spike in result['spikes']:
                # Rate should be positive
                assert spike['rate'] > 0
                # Rate should be magnitude / duration (with positive sign)
                expected_rate = spike['magnitude'] / spike['duration']
                assert spike['rate'] == pytest.approx(expected_rate)
                
    def test_validation_constraints(self):
        """Test that output meets all validation constraints"""
        df = pd.DataFrame({
            'seconds': [0, 1, 2, 3, 4, 5],
            'mode_power': [3500] * 6,
            'summary_wattage': [3200, 3210, 3750, 3760, 3770, 3780],
            'temp_hash_board_max': [60] * 6,
            'psu_temp_max': [40] * 6,
            'outage': [False] * 6
        })
        
        metrics = AnomalyMetrics(df, action_idx=0)
        
        result = metrics.calculate_spikes()
        
        for spike in result['spikes']:
            # All times should be >= 0 (post-action)
            assert spike['time'] >= 0
            # All magnitudes should be positive
            assert spike['magnitude'] > 0
            # All rates should be positive
            assert spike['rate'] > 0
            # end_wattage should be > start_wattage
            assert spike['end_wattage'] > spike['start_wattage']
            # magnitude should equal difference
            assert spike['magnitude'] == pytest.approx(
                spike['end_wattage'] - spike['start_wattage']
            )
            # duration should be > 0 and <= 5 seconds
            assert spike['duration'] > 0
            assert spike['duration'] <= 5.0
            # Spike percentage should be >= 15%
            spike_pct = spike['magnitude'] / spike['start_wattage']
            assert spike_pct >= 0.15


class TestMetric10OvershootUndershoot:
    """Tests for METRIC 10: Overshoot/Undershoot with direction-specific detection"""
    
    def test_overshoot_detection_up_step(self):
        """Test overshoot detection for UP-STEP transition"""
        df = pd.DataFrame({
            'seconds': [0, 10, 20, 30, 40, 50, 60, 70, 80, 90],
            'mode_power': [3500] * 10,
            'summary_wattage': [1500, 2500, 3200, 3750, 3800, 3600, 3520, 3510, 3505, 3500],
            'temp_hash_board_max': [60] * 10,
            'psu_temp_max': [40] * 10,
            'outage': [False] * 10
        })
        
        metrics = AnomalyMetrics(df, action_idx=0)
        target_power = {'after': 3500.0}
        step_direction = {'delta': 2000.0}  # UP-STEP
        
        result = metrics.calculate_overshoot_undershoot(target_power, step_direction)
        
        assert 'overshoot' in result
        assert 'threshold' in result
        assert result['overshoot']['occurred'] is True
        assert result['overshoot']['peak_wattage'] > target_power['after']
        assert result['overshoot']['magnitude'] > 0
        assert result['overshoot']['duration'] > 0
        
    def test_no_overshoot_up_step(self):
        """Test no overshoot detected when staying within threshold"""
        df = pd.DataFrame({
            'seconds': [0, 10, 20, 30, 40, 50, 60],
            'mode_power': [3500] * 7,
            'summary_wattage': [1500, 2500, 3200, 3450, 3480, 3490, 3500],
            'temp_hash_board_max': [60] * 7,
            'psu_temp_max': [40] * 7,
            'outage': [False] * 7
        })
        
        metrics = AnomalyMetrics(df, action_idx=0)
        target_power = {'after': 3500.0}
        step_direction = {'delta': 2000.0}  # UP-STEP
        
        result = metrics.calculate_overshoot_undershoot(target_power, step_direction)
        
        assert result['overshoot']['occurred'] is False
        
    def test_undershoot_detection_down_step(self):
        """Test undershoot detection for DOWN-STEP transition"""
        df = pd.DataFrame({
            'seconds': [0, 10, 20, 30, 40, 50, 60, 70, 80, 90],
            'mode_power': [1000] * 10,
            'summary_wattage': [3500, 2500, 1800, 800, 750, 900, 980, 990, 995, 1000],
            'temp_hash_board_max': [60] * 10,
            'psu_temp_max': [40] * 10,
            'outage': [False] * 10
        })
        
        metrics = AnomalyMetrics(df, action_idx=0)
        target_power = {'after': 1000.0}
        step_direction = {'delta': -2500.0}  # DOWN-STEP
        
        result = metrics.calculate_overshoot_undershoot(target_power, step_direction)
        
        assert 'undershoot' in result
        assert 'threshold' in result
        assert result['undershoot']['occurred'] is True
        assert result['undershoot']['lowest_wattage'] < target_power['after']
        assert result['undershoot']['magnitude'] > 0
        assert result['undershoot']['duration'] > 0
        
    def test_no_undershoot_down_step(self):
        """Test no undershoot detected when staying within threshold"""
        df = pd.DataFrame({
            'seconds': [0, 10, 20, 30, 40, 50, 60],
            'mode_power': [1000] * 7,
            'summary_wattage': [3500, 2500, 1800, 1200, 1050, 1020, 1000],
            'temp_hash_board_max': [60] * 7,
            'psu_temp_max': [40] * 7,
            'outage': [False] * 7
        })
        
        metrics = AnomalyMetrics(df, action_idx=0)
        target_power = {'after': 1000.0}
        step_direction = {'delta': -2500.0}  # DOWN-STEP
        
        result = metrics.calculate_overshoot_undershoot(target_power, step_direction)
        
        assert result['undershoot']['occurred'] is False
        
    def test_threshold_calculation(self):
        """Test that threshold is MAX(200W, 4% of target)"""
        # For 3500W target: 4% = 140W, so threshold = 200W
        df1 = pd.DataFrame({
            'seconds': [0, 10],
            'mode_power': [3500] * 2,
            'summary_wattage': [1500, 3500],
            'temp_hash_board_max': [60] * 2,
            'psu_temp_max': [40] * 2,
            'outage': [False] * 2
        })
        
        metrics1 = AnomalyMetrics(df1, action_idx=0)
        result1 = metrics1.calculate_overshoot_undershoot(
            {'after': 3500.0},
            {'delta': 2000.0}
        )
        assert result1['threshold'] == 200.0
        
        # For 6000W target: 4% = 240W, so threshold = 240W
        df2 = pd.DataFrame({
            'seconds': [0, 10],
            'mode_power': [6000] * 2,
            'summary_wattage': [1500, 6000],
            'temp_hash_board_max': [60] * 2,
            'psu_temp_max': [40] * 2,
            'outage': [False] * 2
        })
        
        metrics2 = AnomalyMetrics(df2, action_idx=0)
        result2 = metrics2.calculate_overshoot_undershoot(
            {'after': 6000.0},
            {'delta': 4500.0}
        )
        assert result2['threshold'] == 240.0
        
    def test_duration_calculation(self):
        """Test accurate duration calculation for transient events"""
        df = pd.DataFrame({
            'seconds': [0, 10, 20, 30, 40, 50, 60, 70],
            'mode_power': [3500] * 8,
            'summary_wattage': [1500, 2500, 3750, 3800, 3750, 3600, 3520, 3500],
            'temp_hash_board_max': [60] * 8,
            'psu_temp_max': [40] * 8,
            'outage': [False] * 8
        })
        
        metrics = AnomalyMetrics(df, action_idx=0)
        target_power = {'after': 3500.0}
        step_direction = {'delta': 2000.0}  # UP-STEP
        
        result = metrics.calculate_overshoot_undershoot(target_power, step_direction)
        
        if result['overshoot']['occurred']:
            # Duration should be reasonable
            assert result['overshoot']['duration'] > 0
            # Peak time should be >= initial crossing time
            assert result['overshoot']['peak_time'] >= result['overshoot']['time']
            
    def test_minimal_step_no_detection(self):
        """Test that MINIMAL-STEP with small delta behaves correctly"""
        df = pd.DataFrame({
            'seconds': [0, 10, 20, 30, 40],
            'mode_power': [3500] * 5,
            'summary_wattage': [3480, 3490, 3495, 3500, 3505],
            'temp_hash_board_max': [60] * 5,
            'psu_temp_max': [40] * 5,
            'outage': [False] * 5
        })
        
        metrics = AnomalyMetrics(df, action_idx=0)
        target_power = {'after': 3500.0}
        step_direction = {'delta': 20.0}  # MINIMAL-STEP
        
        result = metrics.calculate_overshoot_undershoot(target_power, step_direction)
        
        # For small positive delta, checks overshoot
        assert 'overshoot' in result
        # Likely no overshoot for such small change
        assert result['overshoot']['occurred'] is False
        
    def test_validation_constraints_overshoot(self):
        """Test that overshoot output meets all validation constraints"""
        df = pd.DataFrame({
            'seconds': [0, 10, 20, 30, 40, 50, 60],
            'mode_power': [3500] * 7,
            'summary_wattage': [1500, 2500, 3750, 3800, 3750, 3520, 3500],
            'temp_hash_board_max': [60] * 7,
            'psu_temp_max': [40] * 7,
            'outage': [False] * 7
        })
        
        metrics = AnomalyMetrics(df, action_idx=0)
        target_power = {'after': 3500.0}
        step_direction = {'delta': 2000.0}  # UP-STEP
        
        result = metrics.calculate_overshoot_undershoot(target_power, step_direction)
        
        if result['overshoot']['occurred']:
            overshoot = result['overshoot']
            # Time should be >= 0 (post-action)
            assert overshoot['time'] >= 0
            # Peak time should be >= initial crossing time
            assert overshoot['peak_time'] >= overshoot['time']
            # Magnitude should be > threshold
            assert overshoot['magnitude'] > 0
            # Duration should be > 0
            assert overshoot['duration'] > 0
            # Peak wattage should exceed target + threshold
            assert overshoot['peak_wattage'] > target_power['after'] + result['threshold']
            
    def test_validation_constraints_undershoot(self):
        """Test that undershoot output meets all validation constraints"""
        df = pd.DataFrame({
            'seconds': [0, 10, 20, 30, 40, 50, 60],
            'mode_power': [1000] * 7,
            'summary_wattage': [3500, 2500, 750, 700, 750, 980, 1000],
            'temp_hash_board_max': [60] * 7,
            'psu_temp_max': [40] * 7,
            'outage': [False] * 7
        })
        
        metrics = AnomalyMetrics(df, action_idx=0)
        target_power = {'after': 1000.0}
        step_direction = {'delta': -2500.0}  # DOWN-STEP
        
        result = metrics.calculate_overshoot_undershoot(target_power, step_direction)
        
        if result['undershoot']['occurred']:
            undershoot = result['undershoot']
            # Time should be >= 0 (post-action)
            assert undershoot['time'] >= 0
            # Lowest time should be >= initial crossing time
            assert undershoot['lowest_time'] >= undershoot['time']
            # Magnitude should be > 0
            assert undershoot['magnitude'] > 0
            # Duration should be > 0
            assert undershoot['duration'] > 0
            # Lowest wattage should be below target - threshold
            assert undershoot['lowest_wattage'] < target_power['after'] - result['threshold']

