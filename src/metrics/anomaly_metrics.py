"""
Anomaly Detection Metrics Module

Implements METRIC 8 (Sharp Drops) following the pseudocode specification
in R_Test_Metrics_Complete_Pseudocode_v3.md
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
