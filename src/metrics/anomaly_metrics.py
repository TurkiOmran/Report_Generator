"""
Anomaly Detection Metrics Module

Implements anomaly detection metrics following the pseudocode specification
in R_Test_Metrics_Complete_Pseudocode_v3.md:
- METRIC 8: Sharp Drops (15% threshold, 5-second rolling window)
- METRIC 9: Spikes (15% threshold, 5-second rolling window)
- METRIC 10: Overshoot/Undershoot (direction-specific transient detection)
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class AnomalyMetrics:
    """
    Anomaly detection metrics for power profile analysis.
    
    Implements:
    - METRIC 8: Sharp Drops (15% threshold, 5-second rolling window)
    - METRIC 9: Spikes (15% threshold, 5-second rolling window)
    - METRIC 10: Overshoot/Undershoot (direction-specific transient detection)
    """
    
    def __init__(self, df: pd.DataFrame, action_idx: int):
        """
        Initialize AnomalyMetrics calculator.
        
        Args:
            df: Preprocessed DataFrame with required columns
            action_idx: Row index where time crosses 0
        """
        self.df = df
        self.action_idx = action_idx
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def calculate_sharp_drops(self) -> Dict[str, Any]:
        """
        METRIC 8: Sharp Drops
        
        Detect sudden, significant decreases in power that indicate instability,
        control failures, or equipment issues.
        
        Implementation follows pseudocode from:
        R_Test_Metrics_Complete_Pseudocode_v3.md - Lines 1105-1262
        
        Returns:
            Dictionary with sharp_drops list and summary statistics
        """
        # 1. Define detection criteria
        drop_threshold_pct = 0.15  # 15% of current power
        detection_window = 5.0  # seconds
        
        # 2. Extract post-action data
        post_action_mask = self.df.index >= self.action_idx
        post_action = self.df[post_action_mask].copy()
        
        if post_action.empty:
            raise ValueError("No post-action data available")
        
        # 3. Get valid wattage data
        times = post_action['seconds'].values
        wattages = post_action['summary_wattage'].values
        
        # Filter out NaN values
        valid_mask = ~np.isnan(wattages)
        valid_times = times[valid_mask]
        valid_wattages = wattages[valid_mask]
        
        if len(valid_wattages) < 2:
            return {
                'sharp_drops': [],
                'summary': {
                    'count': 0,
                    'worst_magnitude': None,
                    'worst_rate': None
                }
            }
        
        # 4. Scan for sharp drops using rolling window
        sharp_drops = []
        processed_times = set()  # Avoid duplicate detection
        
        for i in range(len(valid_times)):
            current_time = valid_times[i]
            current_wattage = valid_wattages[i]
            
            # Skip if this time already processed in a previous drop
            if current_time in processed_times:
                continue
            
            # Define search window
            window_end_time = current_time + detection_window
            
            # Find all points within window
            window_mask = (valid_times > current_time) & (valid_times <= window_end_time)
            window_times = valid_times[window_mask]
            window_wattages = valid_wattages[window_mask]
            
            if len(window_wattages) == 0:
                continue
            
            # Find minimum wattage in window
            min_wattage = np.min(window_wattages)
            min_idx = np.argmin(window_wattages)
            min_time = window_times[min_idx]
            
            # Calculate drop
            drop_magnitude = current_wattage - min_wattage
            drop_percentage = drop_magnitude / current_wattage
            
            # Check if drop exceeds threshold
            if drop_percentage >= drop_threshold_pct:
                # Sharp drop detected
                drop_duration = min_time - current_time
                drop_rate = -drop_magnitude / drop_duration if drop_duration > 0 else 0
                
                sharp_drops.append({
                    'time': float(current_time),
                    'start_wattage': float(current_wattage),
                    'end_wattage': float(min_wattage),
                    'magnitude': float(drop_magnitude),
                    'duration': float(drop_duration),
                    'rate': float(drop_rate)
                })
                
                # Mark all times in this drop as processed
                for t in window_times[:min_idx + 1]:
                    processed_times.add(t)
        
        # 5. Calculate summary statistics
        if sharp_drops:
            worst_magnitude = max(d['magnitude'] for d in sharp_drops)
            worst_rate = min(d['rate'] for d in sharp_drops)  # Most negative
        else:
            worst_magnitude = None
            worst_rate = None
        
        return {
            'sharp_drops': sharp_drops,
            'summary': {
                'count': len(sharp_drops),
                'worst_magnitude': worst_magnitude,
                'worst_rate': worst_rate
            }
        }
    
    def calculate_spikes(self) -> Dict[str, Any]:
        """
        METRIC 9: Spikes
        
        Detect sudden, significant increases in power that indicate instability,
        overshoot, or control anomalies.
        
        Implementation follows pseudocode from:
        R_Test_Metrics_Complete_Pseudocode_v3.md - Lines 1265-1423
        
        Returns:
            Dictionary with spikes list and summary statistics
        """
        # 1. Define detection criteria
        spike_threshold_pct = 0.15  # 15% of current power
        detection_window = 5.0  # seconds
        
        # 2. Extract post-action data
        post_action_mask = self.df.index >= self.action_idx
        post_action = self.df[post_action_mask].copy()
        
        if post_action.empty:
            raise ValueError("No post-action data available")
        
        # 3. Get valid wattage data
        times = post_action['seconds'].values
        wattages = post_action['summary_wattage'].values
        
        # Filter out NaN values
        valid_mask = ~np.isnan(wattages)
        valid_times = times[valid_mask]
        valid_wattages = wattages[valid_mask]
        
        if len(valid_wattages) < 2:
            return {
                'spikes': [],
                'summary': {
                    'count': 0,
                    'worst_magnitude': None,
                    'worst_rate': None
                }
            }
        
        # 4. Scan for spikes using rolling window
        spikes = []
        processed_times = set()  # Avoid duplicate detection
        
        for i in range(len(valid_times)):
            current_time = valid_times[i]
            current_wattage = valid_wattages[i]
            
            # Skip if this time already processed in a previous spike
            if current_time in processed_times:
                continue
            
            # Define search window
            window_end_time = current_time + detection_window
            
            # Find all points within window
            window_mask = (valid_times > current_time) & (valid_times <= window_end_time)
            window_times = valid_times[window_mask]
            window_wattages = valid_wattages[window_mask]
            
            if len(window_wattages) == 0:
                continue
            
            # Find maximum wattage in window
            max_wattage = np.max(window_wattages)
            max_idx = np.argmax(window_wattages)
            max_time = window_times[max_idx]
            
            # Calculate rise
            rise_magnitude = max_wattage - current_wattage
            rise_percentage = rise_magnitude / current_wattage
            
            # Check if rise exceeds threshold
            if rise_percentage >= spike_threshold_pct:
                # Spike detected
                spike_duration = max_time - current_time
                spike_rate = rise_magnitude / spike_duration if spike_duration > 0 else 0
                
                spikes.append({
                    'time': float(current_time),
                    'start_wattage': float(current_wattage),
                    'end_wattage': float(max_wattage),
                    'magnitude': float(rise_magnitude),
                    'duration': float(spike_duration),
                    'rate': float(spike_rate)
                })
                
                # Mark all times in this spike as processed
                for t in window_times[:max_idx + 1]:
                    processed_times.add(t)
        
        # 5. Calculate summary statistics
        if spikes:
            worst_magnitude = max(s['magnitude'] for s in spikes)
            worst_rate = max(s['rate'] for s in spikes)  # Most positive
        else:
            worst_magnitude = None
            worst_rate = None
        
        return {
            'spikes': spikes,
            'summary': {
                'count': len(spikes),
                'worst_magnitude': worst_magnitude,
                'worst_rate': worst_rate
            }
        }
    
    def calculate_overshoot_undershoot(
        self,
        target_power: Dict[str, Any],
        step_direction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        METRIC 10: Overshoot/Undershoot
        
        Detect when the miner crosses beyond the target power level during
        stabilization, indicating control tuning issues or aggressive response.
        
        Implementation follows pseudocode from:
        R_Test_Metrics_Complete_Pseudocode_v3.md - Lines 1426-1651
        
        Args:
            target_power: Dictionary from METRIC 2
            step_direction: Dictionary from METRIC 3
            
        Returns:
            Dictionary with overshoot or undershoot results and threshold
        """
        # 1. Extract parameters
        target = target_power['after']
        delta = step_direction['delta']
        
        # 2. Calculate threshold
        threshold_absolute = 200  # watts
        threshold_percentage = 0.04  # 4%
        threshold = max(threshold_absolute, target * threshold_percentage)
        
        # 3. Extract post-action data
        post_action_mask = self.df.index >= self.action_idx
        post_action = self.df[post_action_mask].copy()
        
        if post_action.empty:
            raise ValueError("No post-action data available")
        
        # 4. Determine which anomaly to check based on direction
        check_overshoot = (delta > 0)  # Increasing power
        check_undershoot = (delta < 0)  # Decreasing power
        
        # 5. Check for overshoot (if applicable)
        overshoot_result = None
        
        if check_overshoot:
            upper_threshold = target + threshold
            wattage = post_action['summary_wattage']
            
            # Find where wattage exceeds upper threshold
            overshoot_mask = wattage > upper_threshold
            
            if overshoot_mask.any():
                # Overshoot detected
                
                # Find peak overshoot
                peak_idx = wattage.idxmax()
                peak_wattage = wattage.loc[peak_idx]
                peak_time = post_action.loc[peak_idx, 'seconds']
                
                # Find when first crossed threshold
                first_cross_idx = overshoot_mask.idxmax()
                first_cross_time = post_action.loc[first_cross_idx, 'seconds']
                
                # Calculate duration above threshold
                # Find when it drops back below threshold (if it does)
                post_peak_mask = post_action.index > peak_idx
                post_peak_data = post_action[post_peak_mask]
                
                if not post_peak_data.empty:
                    below_threshold_mask = post_peak_data['summary_wattage'] <= upper_threshold
                    
                    if below_threshold_mask.any():
                        return_idx = post_peak_data[below_threshold_mask].index[0]
                        return_time = post_peak_data.loc[return_idx, 'seconds']
                        duration = return_time - first_cross_time
                    else:
                        # Never returned below threshold
                        duration = post_action['seconds'].iloc[-1] - first_cross_time
                else:
                    # Peaked at end of test
                    duration = peak_time - first_cross_time
                
                magnitude = peak_wattage - target
                
                overshoot_result = {
                    'occurred': True,
                    'time': float(first_cross_time),
                    'peak_wattage': float(peak_wattage),
                    'peak_time': float(peak_time),
                    'magnitude': float(magnitude),
                    'duration': float(duration)
                }
            else:
                overshoot_result = {
                    'occurred': False
                }
        
        # 6. Check for undershoot (if applicable)
        undershoot_result = None
        
        if check_undershoot:
            lower_threshold = target - threshold
            wattage = post_action['summary_wattage']
            
            # Find where wattage drops below lower threshold
            undershoot_mask = wattage < lower_threshold
            
            if undershoot_mask.any():
                # Undershoot detected
                
                # Find lowest point
                lowest_idx = wattage.idxmin()
                lowest_wattage = wattage.loc[lowest_idx]
                lowest_time = post_action.loc[lowest_idx, 'seconds']
                
                # Find when first crossed threshold
                first_cross_idx = undershoot_mask.idxmax()
                first_cross_time = post_action.loc[first_cross_idx, 'seconds']
                
                # Calculate duration below threshold
                # Find when it rises back above threshold (if it does)
                post_lowest_mask = post_action.index > lowest_idx
                post_lowest_data = post_action[post_lowest_mask]
                
                if not post_lowest_data.empty:
                    above_threshold_mask = post_lowest_data['summary_wattage'] >= lower_threshold
                    
                    if above_threshold_mask.any():
                        return_idx = post_lowest_data[above_threshold_mask].index[0]
                        return_time = post_lowest_data.loc[return_idx, 'seconds']
                        duration = return_time - first_cross_time
                    else:
                        # Never returned above threshold
                        duration = post_action['seconds'].iloc[-1] - first_cross_time
                else:
                    # Bottomed at end of test
                    duration = lowest_time - first_cross_time
                
                magnitude = target - lowest_wattage
                
                undershoot_result = {
                    'occurred': True,
                    'time': float(first_cross_time),
                    'lowest_wattage': float(lowest_wattage),
                    'lowest_time': float(lowest_time),
                    'magnitude': float(magnitude),
                    'duration': float(duration)
                }
            else:
                undershoot_result = {
                    'occurred': False
                }
        
        # 7. Return appropriate result based on test direction
        if check_overshoot:
            return {
                'overshoot': overshoot_result,
                'threshold': float(threshold)
            }
        else:
            return {
                'undershoot': undershoot_result,
                'threshold': float(threshold)
            }
